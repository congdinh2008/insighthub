import assert from 'node:assert/strict';
import { connectClient } from './test/client.mjs';
import { fixture, CANARY } from './test/fixture.mjs';

const live = process.argv.includes('--live');
if (process.argv.slice(2).some(arg => arg !== '--live')) throw new Error('Usage: node smoke.mjs [--live]');
const backend = live ? null : await fixture();
const env = live ? Object.fromEntries(Object.entries(process.env).filter(([key]) =>
  key.startsWith('INSIGHTHUB_'))) : {
  INSIGHTHUB_API_URL: backend.url,
  INSIGHTHUB_PROMETHEUS_URL: backend.url,
  INSIGHTHUB_MCP_PROMETHEUS: '1',
  INSIGHTHUB_MCP_TOOLS: 'insighthub_health,insighthub_list_documents,prometheus_summary',
};
const expectedTools = (env.INSIGHTHUB_MCP_TOOLS ?? 'insighthub_health,insighthub_list_documents')
  .split(',').map(s => s.trim()).filter(Boolean).sort();
assert.ok(expectedTools.length > 0, 'Smoke requires at least one enabled tool to exercise tools/call');
const results = [];
try {
  for (const mode of ['modern', 'legacy', 'v1', 'auto']) {
    const session = await connectClient(mode, env);
    try {
      // SDK connect probes in a disposable sibling stdio process. Explicitly
      // discover again here so the observed transcript includes the real RPC.
      if (mode === 'modern' || mode === 'auto') await session.client.request({ method: 'server/discover' });
      const listed = await session.client.listTools();
      assert.deepEqual(listed.tools.map(t => t.name).sort(), expectedTools);
      const calls = [];
      for (const name of expectedTools) {
        const args = name === 'insighthub_list_documents' ? { limit: 2 } : name === 'prometheus_summary' ? { query: 'requests_5m' } : {};
        const result = await session.client.callTool({ name, arguments: args });
        assert.notEqual(result.isError, true, name + ' failed');
        assert.ok(result.structuredContent);
        if (name === 'insighthub_health') assert.equal(result.structuredContent.live, true);
        if (name === 'insighthub_list_documents') {
          assert.ok(result.structuredContent.returned <= 2);
          for (const row of result.structuredContent.documents) assert.deepEqual(Object.keys(row).sort(), ['chunk_count', 'id', 'status']);
        }
        calls.push(name);
      }
      const incoming = session.wire.filter(w => w.direction === 'in').map(w => w.message);
      const outgoing = session.wire.filter(w => w.direction === 'out').map(w => w.message);
      const initialize = incoming.find(m => m.result?.protocolVersion);
      const requestVersion = outgoing.find(m => m.method === 'tools/list')?.params?._meta?.['io.modelcontextprotocol/protocolVersion'];
      const protocol = initialize?.result.protocolVersion ?? requestVersion;
      assert.equal(protocol, mode === 'modern' || mode === 'auto' ? '2026-07-28' : '2025-11-25');
      if (mode === 'modern') {
        assert.ok(outgoing.some(m => m.method === 'server/discover'));
        assert.ok(!outgoing.some(m => m.method === 'initialize'));
        assert.ok(incoming.some(m => m.result?.resultType === 'complete'));
      } else if (mode === 'v1' || mode === 'legacy') {
        assert.ok(outgoing.some(m => m.method === 'initialize'));
        assert.ok(outgoing.some(m => m.method === 'notifications/initialized'));
      }
      assert.ok(!JSON.stringify(incoming).includes(CANARY));
      assert.equal(session.stderr(), '');
      results.push({ client: mode === 'v1' ? '@modelcontextprotocol/sdk@1.30.0' : '@modelcontextprotocol/client@2.0.0',
        mode, protocol, methods: [...new Set(outgoing.map(m => m.method).filter(Boolean))], calls, passed: true });
    } finally { await session.client.close(); }
  }
  if (backend) assert.ok(backend.requests.every(r => r.method === 'GET' && r.authorization === undefined));
  console.log(JSON.stringify({ passed: true, backend_mode: live ? 'live' : 'fixture', live,
    backend: live ? 'live-loopback' : 'fixture-loopback',
    node: process.version, server: '@modelcontextprotocol/server@2.0.0', results }, null, 2));
} finally { await backend?.close(); }
