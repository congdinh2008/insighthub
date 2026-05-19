import http from 'node:http';
export const CANARY = 'CANARY_SECRET_DO_NOT_EXPOSE_7c925';
export async function fixture(handler) {
  const requests = [];
  const server = http.createServer((req, res) => {
    requests.push({ method: req.method, url: req.url, authorization: req.headers.authorization });
    if (handler) return handler(req, res);
    res.setHeader('Content-Type', 'application/json');
    if (req.url === '/healthz') res.end(JSON.stringify({ status: 'ok', token: CANARY }));
    else if (req.url === '/readyz') res.end(JSON.stringify({ status: 'ready', db: true, password: CANARY }));
    else if (req.url === '/documents') res.end(JSON.stringify(Array.from({ length: 23 }, (_, i) => ({
      id: i + 1, status: 'ready', chunk_count: 2, filename: CANARY,
      content: CANARY, created_at: CANARY, api_key: CANARY,
    }))));
    else if (req.url.startsWith('/api/v1/query?')) res.end(JSON.stringify({
      status: 'success', data: { resultType: 'vector', result: [{ metric: { token: CANARY }, value: [1, '3'] }] },
      warnings: [CANARY],
    }));
    else { res.statusCode = 404; res.end('{}'); }
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  return {
    url: 'http://127.0.0.1:' + server.address().port, requests,
    close: () => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); }),
  };
}
