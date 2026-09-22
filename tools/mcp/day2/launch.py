#!/usr/bin/env python3
"""Launch pinned upstream MCP servers; stdout remains MCP protocol only."""

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = Path(os.environ.get("INSIGHTHUB_DAY2_STATE", ROOT / "tmp/day2")).resolve()


def definition(name):
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "TMPDIR", "DOCKER_HOST", "DOCKER_CONTEXT"}
    }
    if name == "filesystem":
        env["MCP_GATEWAY_DOCKER_BIND_ALLOWED_PATHS"] = str(STATE / "source-view")
        return [
            str(STATE / "bin/docker-mcp"),
            "gateway",
            "run",
            "--transport=stdio",
            "--servers=filesystem",
            "--watch=false",
            "--log-calls=false",
            "--catalog",
            str(Path.home() / ".docker/mcp/catalogs/insighthub-filesystem.json"),
            "--tools=read_file,list_directory,list_allowed_directories",
        ], env
    if name == "docker":
        binary = str(STATE / "bin/docker-mcp")
        return [
            binary,
            "gateway",
            "run",
            "--transport=stdio",
            "--servers=docker-operations",
            "--static",
            "--watch=false",
            "--log-calls=false",
            "--catalog",
            str(Path.home() / ".docker/mcp/catalogs/insighthub-operations.json"),
            "--config",
            str(STATE / "gateway-config.json"),
            "--registry",
            str(STATE / "gateway-registry.json"),
            "--tools-config",
            str(STATE / "gateway-tools.json"),
            "--secrets",
            str(STATE / "gateway-secrets.env"),
            "--tools=list_containers,get_diagnostic_logs,get_worker_logs",
        ], env
    if name == "kubernetes":
        return [
            str(STATE / "bin/kubernetes-mcp-server"),
            "--kubeconfig",
            str(STATE / "readonly.kubeconfig"),
            "--config",
            str(Path(__file__).with_name("kubernetes.toml")),
            "--read-only",
            "--disable-multi-cluster",
        ], env
    if name == "prometheus":
        return [
            str(STATE / "bin/prometheus-mcp-server"),
            "--mcp.transport=stdio",
            "--prometheus.url=http://127.0.0.1:19092",
            "--web.listen-address=127.0.0.1:0",
            "--mcp.tools=list_targets",
            "--prometheus.timeout=5s",
            "--prometheus.truncation-limit=20",
            "--no-docs.auto-update",
        ], env
    if name == "insighthub":
        env.update(
            INSIGHTHUB_API_URL="http://127.0.0.1:18002",
            INSIGHTHUB_MCP_TOOLS="insighthub_health,insighthub_list_documents",
        )
        return [
            shutil.which("node") or "node",
            str(ROOT / "tools/mcp/src/server.mjs"),
        ], env
    raise SystemExit("Expected filesystem|docker|kubernetes|prometheus|insighthub")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: launch.py <backend>")
    command, environment = definition(sys.argv[1])
    os.chdir(ROOT)
    os.execve(command[0], command, environment)
