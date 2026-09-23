#!/usr/bin/env python3
"""Launch pinned Day 02 MCP binaries against the Day 04 read-only lab."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "tmp" / "day4"
BIN = ROOT / "tmp" / "day2" / "bin"


def definition(name: str) -> tuple[list[str], dict[str, str]]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "TMPDIR"}
    }
    if name == "kubernetes":
        return [
            str(BIN / "kubernetes-mcp-server"),
            "--kubeconfig",
            str(STATE / "readonly.kubeconfig"),
            "--config",
            str(Path(__file__).with_name("kubernetes.toml")),
            "--read-only",
            "--disable-multi-cluster",
        ], environment
    if name == "prometheus":
        return [
            str(BIN / "prometheus-mcp-server"),
            "--mcp.transport=stdio",
            "--prometheus.url=http://127.0.0.1:19090",
            "--web.listen-address=127.0.0.1:0",
            "--mcp.tools=query,range_query,list_targets",
            "--prometheus.timeout=5s",
            "--prometheus.truncation-limit=50",
            "--no-docs.auto-update",
        ], environment
    raise SystemExit("Expected kubernetes|prometheus")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: launch.py <kubernetes|prometheus>")
    command, env = definition(sys.argv[1])
    if not Path(command[0]).is_file():
        raise SystemExit("Run tools/mcp/day2/install.py to install the pinned binary")
    os.chdir(ROOT)
    os.execve(command[0], command, env)
