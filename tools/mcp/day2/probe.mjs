import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const state = process.env.INSIGHTHUB_DAY2_STATE ?? path.join(repo, 'tmp/day2');
const config = JSON.parse(await readFile(path.join(state, 'servers.json'), 'utf8'));
const selected = process.argv[2] ?? 'all';
const callsFile = process.argv[3];
const calls = callsFile ? JSON.parse(await readFile(callsFile, 'utf8')) : {};
const results = [];
for (const [name, launch] of Object.entries(config)) {
  if (selected !== 'all' && name !== selected) continue;
  const record = { server: name, observed_at: new Date().toISOString(), backend_mode: 'live', calls: [] };
  const wire = [];
  const transport = new StdioClientTransport({ command: launch.command, args: launch.args,
    env: { PATH: process.env.PATH, HOME: process.env.HOME, ...launch.env }, stderr: 'pipe' });
  let stderr = '';
  transport.stderr?.on('data', chunk => { stderr = (stderr + chunk).slice(-3000); });
  const send = transport.send.bind(transport);
  transport.send = async (...args) => { wire.push({ out: args[0] }); return send(...args); };
  const start = transport.start.bind(transport);
  transport.start = async () => {
    const receive = transport.onmessage;
    transport.onmessage = (message, extra) => { wire.push({ in: message }); receive?.(message, extra); };
    await start();
  };
  const client = new Client({ name: 'insighthub-mcp-verification', version: '1.0.0' }, {
    versionNegotiation: { mode: 'auto' },
  });
  try {
    await client.connect(transport, { timeout: 60000 });
    const listing = await client.listTools();
    record.tools = listing.tools;
    for (const call of calls[name] ?? []) {
      const entry = { name: call.name, arguments: call.arguments ?? {}, expected: call.expected ?? 'success', observed_at: new Date().toISOString() };
      try {
        // request() deliberately avoids client-side schema rejection in deny tests.
        entry.output = await client.request({ method: 'tools/call', params: { name: call.name, arguments: entry.arguments } }, undefined, { timeout: 30000 });
        entry.denied = entry.output.isError === true;
      } catch (error) { entry.denied = true; entry.error = error.message; }
      entry.passed = entry.expected === 'deny' ? entry.denied : !entry.denied;
      record.calls.push(entry);
    }
    record.protocol = wire.find(w => w.in?.result?.protocolVersion)?.in.result.protocolVersion
      ?? wire.find(w => w.out?.method === 'tools/list')?.out.params?._meta?.['io.modelcontextprotocol/protocolVersion'];
    record.methods = [...new Set(wire.map(w => w.out?.method).filter(Boolean))];
    record.passed = record.calls.every(call => call.passed);
  } catch (error) { record.passed = false; record.error = error.message; record.stderr = stderr; }
  finally { await client.close().catch(() => {}); await transport.close().catch(() => {}); }
  results.push(record);
  console.log(JSON.stringify({ server: name, passed: record.passed, protocol: record.protocol, tools: record.tools?.map(t => t.name), error: record.error, stderr: record.stderr, calls: record.calls.map(c => ({ name: c.name, passed: c.passed, error: c.error, output: c.output })) }));
}
await writeFile(path.join(state, `probe-${selected}.json`), JSON.stringify({ observed_at: new Date().toISOString(), results }, null, 2) + '\n');
if (!results.length || results.some(r => !r.passed)) process.exitCode = 1;
