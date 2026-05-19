import { fileURLToPath } from 'node:url';

const mode = process.argv[2];
if (process.argv.length !== 3 || !['claude', 'codex', 'antigravity'].includes(mode)) {
  console.error('Usage: node tools/mcp/host-config.mjs claude|codex|antigravity');
  process.exitCode = 1;
} else {
  const command = process.execPath;
  const entry = fileURLToPath(new URL('./src/server.mjs', import.meta.url));
  const env = {
    INSIGHTHUB_API_URL: 'http://127.0.0.1:8000',
    INSIGHTHUB_MCP_TOOLS: 'insighthub_health,insighthub_list_documents',
    INSIGHTHUB_MCP_PROMETHEUS: '0',
    INSIGHTHUB_MCP_TIMEOUT_MS: '1500',
    INSIGHTHUB_MCP_MAX_BYTES: '65536',
  };
  if (mode !== 'codex') {
    console.log(JSON.stringify({ mcpServers: { 'insighthub-readonly': {
      ...(mode === 'claude' ? { type: 'stdio' } : {}), command, args: [entry], env,
    } } }, null, 2));
  } else {
    console.log([
      '[mcp_servers.insighthub-readonly]',
      'command = ' + JSON.stringify(command),
      'args = ' + JSON.stringify([entry]),
      'startup_timeout_sec = 10',
      'tool_timeout_sec = 10',
      'enabled_tools = ["insighthub_health", "insighthub_list_documents"]',
      '',
      '[mcp_servers.insighthub-readonly.env]',
      ...Object.entries(env).map(([key,value]) => key + ' = ' + JSON.stringify(value)),
    ].join('\n'));
  }
}
