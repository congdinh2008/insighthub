import http from 'node:http';

export const TOOL_NAMES = Object.freeze(['insighthub_health', 'insighthub_list_documents', 'prometheus_summary']);
export const QUERIES = Object.freeze({
  requests_5m: 'sum(increase(insighthub_http_requests_total[5m]))',
  errors_5m: 'sum(increase(insighthub_http_requests_total{status=~"5.."}[5m]))',
  documents: 'sum(insighthub_documents_total)',
});
export class SafeError extends Error {
  constructor(code) { super(code); this.code = code; }
}
const fail = (code) => { throw new SafeError(code); };

export function loopbackOrigin(raw) {
  // Validate the spelling before URL normalization: reject integer/hex IPv4,
  // userinfo, DNS names, path/query injection, fragments and whitespace.
  if (typeof raw !== 'string' || !/^http:\/\/(127\.0\.0\.1|localhost|\[::1\])(?::([1-9][0-9]{0,4}))?\/?$/.test(raw)) {
    fail('INVALID_ORIGIN');
  }
  let url;
  try { url = new URL(raw); } catch { fail('INVALID_ORIGIN'); }
  if (url.hostname === 'localhost') url.hostname = '127.0.0.1';
  return url.origin;
}
function integer(raw, fallback, max, code) {
  if (raw === undefined) return fallback;
  if (!/^[1-9][0-9]*$/.test(raw) || !Number.isSafeInteger(Number(raw)) || Number(raw) > max) fail(code);
  return Number(raw);
}
export function readConfig(env = process.env) {
  const enabled = (env.INSIGHTHUB_MCP_TOOLS ?? 'insighthub_health,insighthub_list_documents')
    .split(',').map(s => s.trim()).filter(Boolean);
  if (enabled.some(n => !TOOL_NAMES.includes(n)) || new Set(enabled).size !== enabled.length) fail('INVALID_TOOL_ALLOWLIST');
  if (env.INSIGHTHUB_MCP_PROMETHEUS !== undefined && !['0', '1'].includes(env.INSIGHTHUB_MCP_PROMETHEUS)) fail('INVALID_PROMETHEUS_FLAG');
  const prometheus = env.INSIGHTHUB_MCP_PROMETHEUS === '1';
  if (enabled.includes('prometheus_summary') && !prometheus) fail('PROMETHEUS_DISABLED');
  return Object.freeze({
    enabled: Object.freeze(enabled),
    api: loopbackOrigin(env.INSIGHTHUB_API_URL ?? 'http://127.0.0.1:8000'),
    prometheus: prometheus ? loopbackOrigin(env.INSIGHTHUB_PROMETHEUS_URL ?? 'http://127.0.0.1:9090') : null,
    timeoutMs: integer(env.INSIGHTHUB_MCP_TIMEOUT_MS, 1500, 5000, 'INVALID_TIMEOUT'),
    maxBytes: integer(env.INSIGHTHUB_MCP_MAX_BYTES, 65536, 262144, 'INVALID_BODY_LIMIT'),
  });
}

// Fixed route capability: the model cannot provide an origin, path or headers.
export function getJson(config, route, query, signal) {
  let url;
  if (route === 'health') url = new URL('/healthz', config.api);
  else if (route === 'ready') url = new URL('/readyz', config.api);
  else if (route === 'documents') url = new URL('/documents', config.api);
  else if (route === 'prometheus' && config.prometheus && Object.hasOwn(QUERIES, query)) {
    url = new URL('/api/v1/query', config.prometheus);
    url.searchParams.set('query', QUERIES[query]);
    url.searchParams.set('timeout', '1s');
  } else return Promise.reject(new SafeError('ENDPOINT_DENIED'));
  // Revalidate even for callers outside the MCP registration layer.
  loopbackOrigin(url.origin);
  return new Promise((resolve, reject) => {
    let done = false;
    let req;
    let timer;
    const finish = (error, value) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      signal?.removeEventListener('abort', abort);
      if (error) { req?.destroy(); reject(error); } else resolve(value);
    };
    const abort = () => finish(new SafeError('CANCELLED'));
    if (signal?.aborted) { abort(); return; }
    signal?.addEventListener('abort', abort, { once: true });
    // node:http does not use HTTP_PROXY, redirects, cookies or automatic retries.
    req = http.get(url, {
      agent: false,
      maxHeaderSize: 8192,
      headers: { Accept: 'application/json', 'Accept-Encoding': 'identity' },
    }, res => {
      const code = res.statusCode;
      if (!(code === 200 || (route === 'ready' && code === 503))) {
        finish(new SafeError('UPSTREAM_HTTP_ERROR')); return;
      }
      const length = Number(res.headers['content-length']);
      if (Number.isFinite(length) && length > config.maxBytes) { finish(new SafeError('BODY_LIMIT')); return; }
      if (res.headers['content-encoding'] && res.headers['content-encoding'] !== 'identity') { finish(new SafeError('ENCODING_DENIED')); return; }
      if ((res.headers['content-type'] ?? '').split(';')[0].trim().toLowerCase() !== 'application/json') {
        finish(new SafeError('INVALID_CONTENT_TYPE')); return;
      }
      let size = 0;
      const chunks = [];
      res.on('data', chunk => {
        size += chunk.length;
        if (size > config.maxBytes) { finish(new SafeError('BODY_LIMIT')); return; }
        chunks.push(chunk);
      });
      res.on('error', () => finish(new SafeError('UPSTREAM_UNAVAILABLE')));
      res.on('aborted', () => finish(new SafeError('UPSTREAM_UNAVAILABLE')));
      res.on('end', () => {
        if (done) return;
        let data;
        try { data = JSON.parse(Buffer.concat(chunks).toString('utf8')); }
        catch { finish(new SafeError('INVALID_JSON')); return; }
        finish(null, { httpStatus: code, data });
      });
    });
    req.on('error', () => finish(new SafeError('UPSTREAM_UNAVAILABLE')));
    // Absolute deadline includes headers and full streamed body, not inactivity.
    timer = setTimeout(() => finish(new SafeError('UPSTREAM_TIMEOUT')), config.timeoutMs);
  });
}
const nonnegative = value => Number.isSafeInteger(value) && value >= 0;
const result = structuredContent => ({ content: [{ type: 'text', text: JSON.stringify(structuredContent) }], structuredContent });

export function createService(config) {
  let active = 0;
  return async function call(name, args, signal) {
    if (!TOOL_NAMES.includes(name) || !config.enabled.includes(name)) fail('TOOL_DENIED');
    if (active >= 4) fail('BUSY');
    if (!args || typeof args !== 'object' || Array.isArray(args)) fail('INVALID_ARGUMENTS');
    const allowedKeys = name === 'insighthub_list_documents' ? ['limit'] : name === 'prometheus_summary' ? ['query'] : [];
    if (Object.keys(args).some(k => !allowedKeys.includes(k))) fail('INVALID_ARGUMENTS');
    active++;
    try {
      if (name === 'insighthub_health') {
        const [live, ready] = await Promise.all([
          getJson(config, 'health', undefined, signal), getJson(config, 'ready', undefined, signal),
        ]);
        if (live.data?.status !== 'ok' ||
          !((ready.httpStatus === 200 && ready.data?.status === 'ready' && ready.data.db === true) ||
            (ready.httpStatus === 503 && ready.data?.status === 'not_ready' && ready.data.db === false))) fail('UPSTREAM_SCHEMA');
        return result({ live: true, ready: ready.httpStatus === 200, databaseReady: ready.data.db });
      }
      if (name === 'insighthub_list_documents') {
        const limit = args.limit ?? 10;
        if (!Number.isInteger(limit) || limit < 1 || limit > 20) fail('INVALID_ARGUMENTS');
        const { data } = await getJson(config, 'documents', undefined, signal);
        if (!Array.isArray(data)) fail('UPSTREAM_SCHEMA');
        const documents = data.slice(0, limit).map(row => {
          if (!row || !Number.isSafeInteger(row.id) || row.id < 1 || !nonnegative(row.chunk_count) ||
            !['pending', 'processing', 'ready', 'failed'].includes(row.status)) fail('UPSTREAM_SCHEMA');
          // Projection, never string-based "secret detection": omit even filenames.
          return { id: row.id, status: row.status, chunk_count: row.chunk_count };
        });
        return result({ documents, returned: documents.length, truncated: data.length > limit });
      }
      if (!config.prometheus || !Object.hasOwn(QUERIES, args.query)) fail('INVALID_ARGUMENTS');
      const { data } = await getJson(config, 'prometheus', args.query, signal);
      if (data?.status !== 'success' || data.data?.resultType !== 'vector' ||
        !Array.isArray(data.data.result) || data.data.result.length > 1) fail('UPSTREAM_SCHEMA');
      const sample = data.data.result[0]?.value;
      let value = null;
      if (sample !== undefined) {
        if (!Array.isArray(sample) || sample.length !== 2 || typeof sample[1] !== 'string' ||
          !/^-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:e[+-]?[0-9]+)?$/i.test(sample[1])) fail('UPSTREAM_SCHEMA');
        value = Number(sample[1]);
        if (!Number.isFinite(value) || value < 0) fail('UPSTREAM_SCHEMA');
      }
      // Drop all upstream labels, annotations, warnings and timestamps.
      return result({ query: args.query, value, window: args.query === 'documents' ? 'instant' : '5m' });
    } finally { active--; }
  };
}
