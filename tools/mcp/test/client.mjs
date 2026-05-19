import { Client } from '@modelcontextprotocol/client';
import { StdioClientTransport } from '@modelcontextprotocol/client/stdio';
import { Client as LegacyClient } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport as LegacyTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { fileURLToPath } from 'node:url';

export async function connectClient(mode, env = {}) {
  const wire = [];
  const modernPackage = mode !== 'v1';
  const transport = new (modernPackage ? StdioClientTransport : LegacyTransport)({
    command: process.execPath,
    args: [fileURLToPath(new URL('../src/server.mjs', import.meta.url))],
    env, stderr: 'pipe',
  });
  let stderr = '';
  transport.stderr?.on('data', chunk => { stderr = (stderr + chunk).slice(-8192); });
  const send = transport.send.bind(transport);
  transport.send = async (message, options) => {
    wire.push({ direction: 'out', message });
    return send(message, options);
  };
  const originalStart = transport.start.bind(transport);
  transport.start = async () => {
    const receive = transport.onmessage;
    transport.onmessage = (message, extra) => {
      wire.push({ direction: 'in', message });
      receive?.(message, extra);
    };
    await originalStart();
  };
  const options = modernPackage ? {
    versionNegotiation: { mode: mode === 'modern' ? { pin: '2026-07-28' } : mode === 'auto' ? 'auto' : 'legacy' },
  } : {};
  const client = new (modernPackage ? Client : LegacyClient)({ name: 'insighthub-sdk-smoke', version: '1.0.0' }, options);
  try { await client.connect(transport, { timeout: 5000 }); }
  catch (error) { await transport.close(); throw error; }
  return { client, transport, wire, stderr: () => stderr };
}
