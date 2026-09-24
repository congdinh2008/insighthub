"""Runtime MCP client using the pinned Day 02 server binaries."""

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ALLOWED = {
    "kubernetes": {"pods_list_in_namespace", "pods_get", "events_list", "pods_log"},
    "prometheus": {"query", "range_query"},
}


class MCPUnavailable(Exception):
    pass


async def call(config_path: str, backend: str, tool: str,
               arguments: dict[str, Any]) -> Any:
    if backend not in ALLOWED or tool not in ALLOWED[backend]:
        raise MCPUnavailable("tool denied")
    try:
        servers = json.loads(Path(config_path).read_text())
        launch = servers[backend]
        if tool not in launch["enabled_tools"]:
            raise MCPUnavailable("tool not configured")
        params = StdioServerParameters(command=launch["command"], args=launch["args"],
                                       env=launch.get("env"))
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer,
                                     read_timeout_seconds=timedelta(seconds=10)) as session:
                await session.initialize()
                listed = await session.list_tools()
                if tool not in {item.name for item in listed.tools}:
                    raise MCPUnavailable("tool missing from MCP server")
                result = await session.call_tool(tool, arguments,
                                                 read_timeout_seconds=timedelta(seconds=10))
                if result.isError:
                    raise MCPUnavailable("MCP tool returned error")
                if result.structuredContent is not None:
                    return result.structuredContent
                texts = [item.text for item in result.content if item.type == "text"]
                if not texts:
                    raise MCPUnavailable("MCP returned empty result")
                parsed: list[Any] = []
                for value in texts:
                    try:
                        parsed.append(json.loads(value))
                    except ValueError:
                        parsed.append(value)
                return parsed[0] if len(parsed) == 1 else parsed
    except MCPUnavailable:
        raise
    except Exception as exc:
        raise MCPUnavailable(type(exc).__name__) from None
