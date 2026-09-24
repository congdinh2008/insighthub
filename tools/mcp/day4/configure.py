#!/usr/bin/env python3
"""Create a short-lived namespace-scoped kubeconfig and local MCP config."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "tmp" / "day4"
CONTEXT = "kind-insighthub-local"
NAMESPACE = "insighthub-dev"
SERVICE_ACCOUNT = "insighthub-day4-mcp-readonly"


def run(*arguments: str) -> str:
    return subprocess.check_output(arguments, cwd=ROOT, text=True).strip()


def main() -> None:
    kubectl = shutil.which("kubectl")
    if not kubectl:
        raise SystemExit("kubectl is required")
    if run(kubectl, "config", "current-context") != CONTEXT:
        raise SystemExit(f"Select {CONTEXT} before configuring Day 04 MCP")
    STATE.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700)

    cluster = json.loads(
        run(
            kubectl,
            "--context",
            CONTEXT,
            "config",
            "view",
            "--raw",
            "--minify",
            "-o",
            "json",
        )
    )["clusters"][0]["cluster"]
    token = run(
        kubectl,
        "--context",
        CONTEXT,
        "-n",
        NAMESPACE,
        "create",
        "token",
        SERVICE_ACCOUNT,
        "--duration=6h",
    )
    kubeconfig = {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [{"name": "day4", "cluster": cluster}],
        "users": [{"name": "day4-readonly", "user": {"token": token}}],
        "contexts": [
            {
                "name": "insighthub-day4-readonly",
                "context": {
                    "cluster": "day4",
                    "user": "day4-readonly",
                    "namespace": NAMESPACE,
                },
            }
        ],
        "current-context": "insighthub-day4-readonly",
    }
    kubeconfig_path = STATE / "readonly.kubeconfig"
    kubeconfig_path.write_text(json.dumps(kubeconfig, indent=2) + "\n")
    kubeconfig_path.chmod(0o600)

    launcher = str(Path(__file__).with_name("launch.py"))
    servers = {
        name: {
            "command": str(Path(sys.executable).resolve()),
            "args": [launcher, name],
            "enabled_tools": tools,
            "startup_timeout_sec": 60,
            "tool_timeout_sec": 30,
        }
        for name, tools in {
            "kubernetes": [
                "pods_list_in_namespace",
                "pods_get",
                "pods_log",
                "events_list",
            ],
            "prometheus": ["query", "range_query", "list_targets"],
        }.items()
    }
    (STATE / "servers.json").write_text(json.dumps(servers, indent=2) + "\n")
    config = []
    for name, server in servers.items():
        config.append(f"[mcp_servers.{name}]")
        for key, value in server.items():
            config.append(f"{key} = {json.dumps(value)}")
        config.append("")
    (STATE / "codex.config.toml").write_text("\n".join(config))
    print(f"Generated {kubeconfig_path} and {STATE / 'codex.config.toml'}")


if __name__ == "__main__":
    main()
