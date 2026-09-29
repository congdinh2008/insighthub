#!/usr/bin/env python3
"""Launch Day 02-pinned MCP binaries with Day 05 read-only scope."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "tmp" / "day5"
BIN = ROOT / "tmp" / "day2" / "bin"


def definition(name: str) -> list[str]:
    if name == "kubernetes":
        return [str(BIN / "kubernetes-mcp-server"), "--kubeconfig",
                str(STATE / "readonly.kubeconfig"), "--config",
                str(Path(__file__).with_name("kubernetes.toml")),
                "--read-only", "--disable-multi-cluster"]
    if name == "prometheus":
        return [str(BIN / "prometheus-mcp-server"), "--mcp.transport=stdio",
                "--prometheus.url=http://127.0.0.1:19090",
                "--web.listen-address=127.0.0.1:0",
                "--mcp.tools=query", "--mcp.tools=range_query", "--prometheus.timeout=5s",
                "--prometheus.truncation-limit=50", "--no-docs.auto-update"]
    raise SystemExit("Expected kubernetes|prometheus")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: launch.py <kubernetes|prometheus>")
    command = definition(sys.argv[1])
    if not Path(command[0]).is_file():
        raise SystemExit("Install the Day 02-pinned MCP binaries")
    env = {key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR") if key in os.environ}
    os.chdir(ROOT)
    os.execve(command[0], command, env)
