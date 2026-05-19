import test from 'node:test';
import assert from 'node:assert/strict';
import { readConfig, loopbackOrigin, getJson, createService, QUERIES } from '../src/core.mjs';
import { fixture, CANARY } from './fixture.mjs';

test('origin parser rejects SSRF, DNS/rebinding, path and credential inputs', () => {
  for (const origin of ['https://127.0.0.1', 'http://example.org', 'http://169.254.169.254',
    'http://10.0.0.1', 'http://0.0.0.0', 'http://127.0.0.2', 'http://2130706433',
    'http://0x7f000001', 'http://127.1', 'http://localhost.evil', 'http://user:pass@127.0.0.1',
    'http://127.0.0.1/../documents', 'http://127.0.0.1?url=evil', 'http://127.0.0.1/#x',
    'http://[::ffff:127.0.0.1]', 'http://127.0.0.1:65536', ' http://127.0.0.1', 'file:///etc/passwd']) {
    assert.throws(() => loopbackOrigin(origin), /INVALID_ORIGIN/, origin);
  }
  assert.equal(loopbackOrigin('http://localhost:8000/'), 'http://127.0.0.1:8000');
  assert.equal(loopbackOrigin('http://[::1]:8000'), 'http://[::1]:8000');
});
test('configuration is closed by default and fails on misspelled controls', () => {
  assert.deepEqual(readConfig({}).enabled, ['insighthub_health', 'insighthub_list_documents']);
  assert.equal(readConfig({}).prometheus, null);
  assert.deepEqual(readConfig({ INSIGHTHUB_MCP_TOOLS: '' }).enabled, []);
  for (const env of [
    { INSIGHTHUB_MCP_TOOLS: 'shell' }, { INSIGHTHUB_MCP_TOOLS: 'insighthub_health,insighthub_health' },
    { INSIGHTHUB_MCP_TOOLS: 'prometheus_summary' }, { INSIGHTHUB_MCP_PROMETHEUS: 'yes' },
    { INSIGHTHUB_MCP_TIMEOUT_MS: '5001' }, { INSIGHTHUB_MCP_TIMEOUT_MS: '0' },
    { INSIGHTHUB_MCP_TIMEOUT_MS: 'NaN' }, { INSIGHTHUB_MCP_MAX_BYTES: '262145' },
  ]) assert.throws(() => readConfig(env));
});
test('service projects metadata, limits rows, uses only fixed GET routes', async t => {
  const f = await fixture(); t.after(f.close);
  const config = readConfig({ INSIGHTHUB_API_URL: f.url });
  const call = createService(config);
  const health = await call('insighthub_health', {});
  assert.deepEqual(health.structuredContent, { live: true, ready: true, databaseReady: true });
  const docs = await call('insighthub_list_documents', { limit: 1 });
  assert.deepEqual(docs.structuredContent, { documents: [{ id: 1, status: 'ready', chunk_count: 2 }], returned: 1, truncated: true });
  assert.ok(!JSON.stringify([health, docs]).includes(CANARY));
  for (const args of [{limit:0}, {limit:21}, {limit:1.5}, {limit:'2'}, {content:true}, {url:'http://evil'}, {command:'id'}])
    await assert.rejects(call('insighthub_list_documents', args), /INVALID_ARGUMENTS/);
  await assert.rejects(call('prometheus_summary', { query: 'documents' }), /TOOL_DENIED/);
  await assert.rejects(getJson(config, '/documents/1'), /ENDPOINT_DENIED/);
  await assert.rejects(getJson(config, 'prometheus', 'documents'), /ENDPOINT_DENIED/);
  assert.deepEqual(f.requests.map(r => r.url).sort(), ['/documents','/healthz','/readyz']);
  assert.ok(f.requests.every(r => r.method === 'GET' && r.authorization === undefined));
});
test('readiness 503 is a valid unhealthy observation', async t => {
  const f = await fixture((req,res) => {
    res.setHeader('Content-Type','application/json');
    if(req.url === '/readyz') { res.statusCode = 503; res.end('{"status":"not_ready","db":false}'); }
    else res.end('{"status":"ok"}');
  }); t.after(f.close);
  const output = await createService(readConfig({INSIGHTHUB_API_URL:f.url}))('insighthub_health',{});
  assert.equal(output.structuredContent.ready, false);
});
test('Prometheus allows only fixed aggregate queries and drops labels', async t => {
  const f = await fixture(); t.after(f.close);
  const config = readConfig({ INSIGHTHUB_MCP_TOOLS:'prometheus_summary', INSIGHTHUB_MCP_PROMETHEUS:'1', INSIGHTHUB_PROMETHEUS_URL:f.url });
  const call = createService(config);
  for (const query of Object.keys(QUERIES)) {
    const output = await call('prometheus_summary', {query});
    assert.equal(output.structuredContent.value,3);
    assert.ok(!JSON.stringify(output).includes(CANARY));
    const url = new URL(f.requests.at(-1).url, f.url);
    assert.equal(url.searchParams.get('query'),QUERIES[query]);
    assert.equal(url.searchParams.get('timeout'),'1s');
  }
  for (const args of [{query:'up'}, {query:'documents', start:0}, {query:'__proto__'}, {query:'requests_5m',url:f.url}])
    await assert.rejects(call('prometheus_summary',args),/INVALID_ARGUMENTS/);
  assert.equal(f.requests.length,3);
});
for (const [label, handler, expected] of [
  ['redirect', (req,res) => {res.writeHead(302,{Location:'http://169.254.169.254/latest/meta-data/'});res.end(CANARY);}, 'UPSTREAM_HTTP_ERROR'],
  ['declared body limit', (req,res) => {res.writeHead(200,{'Content-Type':'application/json','Content-Length':'1000000'});res.end('{}');}, 'BODY_LIMIT'],
  ['chunked body limit', (req,res) => {res.writeHead(200,{'Content-Type':'application/json'});res.write(' '.repeat(40000));res.end(' '.repeat(40000));}, 'BODY_LIMIT'],
  ['malformed JSON', (req,res) => {res.setHeader('Content-Type','application/json');res.end(CANARY);}, 'INVALID_JSON'],
  ['wrong content type', (req,res) => {res.setHeader('Content-Type','text/html');res.end(CANARY);}, 'INVALID_CONTENT_TYPE'],
  ['compressed body', (req,res) => {res.writeHead(200,{'Content-Type':'application/json','Content-Encoding':'gzip'});res.end(CANARY);}, 'ENCODING_DENIED'],
  ['upstream error', (req,res) => {res.writeHead(500,{'Content-Type':'application/json'});res.end(CANARY);}, 'UPSTREAM_HTTP_ERROR'],
  ['slow headers', () => {}, 'UPSTREAM_TIMEOUT'],
  ['slow body', (req,res) => {res.writeHead(200,{'Content-Type':'application/json'});res.write('{');}, 'UPSTREAM_TIMEOUT'],
]) test(label + ' fails closed without reflecting body', async t => {
  const f = await fixture(handler); t.after(f.close);
  const config = readConfig({ INSIGHTHUB_API_URL:f.url, INSIGHTHUB_MCP_TIMEOUT_MS:'150' });
  const start = performance.now();
  await assert.rejects(getJson(config,'documents'), error => error.code === expected && !error.message.includes(CANARY));
  assert.ok(performance.now() - start < 2000);
  assert.equal(f.requests.length,1);
});
test('malicious metadata and malformed metrics fail instead of leaking', async t => {
  const f = await fixture((req,res) => {
    res.setHeader('Content-Type','application/json');
    res.end(req.url === '/documents' ? JSON.stringify([{id:1,status:CANARY,chunk_count:1}]) :
      JSON.stringify({status:'success',data:{resultType:'vector',result:[{value:[1,CANARY]}]}}));
  });t.after(f.close);
  const call = createService(readConfig({INSIGHTHUB_API_URL:f.url, INSIGHTHUB_PROMETHEUS_URL:f.url,
    INSIGHTHUB_MCP_PROMETHEUS:'1',INSIGHTHUB_MCP_TOOLS:'insighthub_list_documents,prometheus_summary'}));
  await assert.rejects(call('insighthub_list_documents',{}),/UPSTREAM_SCHEMA/);
  await assert.rejects(call('prometheus_summary',{query:'documents'}),/UPSTREAM_SCHEMA/);
});
test('cancellation and maximum four concurrent tool calls are enforced', async t => {
  const f = await fixture(() => {});t.after(f.close);
  const call = createService(readConfig({INSIGHTHUB_API_URL:f.url,INSIGHTHUB_MCP_TIMEOUT_MS:'200'}));
  const controller = new AbortController();
  const pending = Array.from({length:4}, () => call('insighthub_list_documents',{},controller.signal));
  const settled = Promise.allSettled(pending);
  await assert.rejects(call('insighthub_list_documents',{}),/BUSY/);
  controller.abort();
  const results = await settled;
  assert.ok(results.every(r => r.status === 'rejected' && r.reason.code === 'CANCELLED'));
});
