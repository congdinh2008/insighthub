import { McpServer } from '@modelcontextprotocol/server';
import { serveStdio, StdioServerTransport } from '@modelcontextprotocol/server/stdio';
import { z } from 'zod';
import { createService, readConfig, SafeError } from './core.mjs';

const annotations = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false };
const definitions = {
  insighthub_health: {
    description: 'Read local InsightHub liveness and DB readiness. Returns booleans only.',
    inputSchema: z.strictObject({}),
  },
  insighthub_list_documents: {
    description: 'List up to 20 local document IDs, status and chunk counts. No filenames or content.',
    inputSchema: z.strictObject({ limit: z.number().int().min(1).max(20).optional() }),
  },
  prometheus_summary: {
    description: 'Read one aggregate InsightHub metric via a fixed 5-minute or instant query. No labels.',
    inputSchema: z.strictObject({ query: z.enum(['requests_5m', 'errors_5m', 'documents']) }),
  },
};

export function buildServer(config) {
  const server = new McpServer({ name: 'insighthub-readonly', version: '1.0.0' }, { capabilities: { tools: {} } });
  const call = createService(config);
  for (const name of config.enabled) {
    server.registerTool(name, { ...definitions[name], annotations }, async (args, ctx) => {
      try { return await call(name, args, ctx.mcpReq.signal); }
      catch (error) {
        return { isError: true, content: [{ type: 'text', text: error instanceof SafeError ? error.code : 'INTERNAL_ERROR' }] };
      }
    });
  }
  return server;
}

try {
  if (process.argv.length > 2) throw new SafeError('UNEXPECTED_ARGUMENTS');
  const config = readConfig();
  const stdio = new StdioServerTransport(process.stdin, process.stdout, { maxBufferSize: 65536 });
  // Preserve SDK protocol framing but remove reflected inputs from SDK errors
  // (unknown tool names or schema errors may otherwise include caller secrets).
  const send = stdio.send.bind(stdio);
  stdio.send = async (message, options) => {
    if (message.error) message = { ...message, error: { code: message.error.code, message: 'MCP request rejected' } };
    else if (message.result?.isError) {
      message = { ...message, result: {
        ...message.result, content: [{ type: 'text', text: 'READ_ONLY_REQUEST_FAILED' }],
        structuredContent: undefined,
      } };
    }
    return send(message, options);
  };
  const handle = serveStdio(() => buildServer(config), {
    transport: stdio, legacy: 'serve', onerror: () => console.error('MCP_TRANSPORT_ERROR'),
  });
  process.on('SIGINT', () => { void handle.close(); });
  process.on('SIGTERM', () => { void handle.close(); });
} catch {
  console.error('MCP_STARTUP_REJECTED: check tools/mcp/README.md configuration.');
  process.exitCode = 1;
}
