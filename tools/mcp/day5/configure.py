#!/usr/bin/env python3
"""Generate Day 05 scoped credentials/config in ignored tmp/day5 only."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "tmp" / "day5"
CONTEXT = "kind-insighthub-local"
NAMESPACE = "insighthub-dev"


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True, cwd=ROOT,
                                   stderr=subprocess.DEVNULL).strip()


def kubeconfig(cluster: dict, token: str, user: str) -> dict:
    return {
        "apiVersion": "v1", "kind": "Config",
        "clusters": [{"name": "day5", "cluster": cluster}],
        "users": [{"name": user, "user": {"token": token}}],
        "contexts": [{"name": CONTEXT, "context": {
            "cluster": "day5", "user": user, "namespace": NAMESPACE}}],
        "current-context": CONTEXT,
    }


def main() -> None:
    kubectl = shutil.which("kubectl")
    if not kubectl or run(kubectl, "config", "current-context") != CONTEXT:
        raise SystemExit(f"Select {CONTEXT} first")
    STATE.mkdir(parents=True, exist_ok=True)
    STATE.chmod(0o700)
    cluster = json.loads(run(kubectl, "--context", CONTEXT, "config", "view",
                             "--raw", "--minify", "-o", "json"))["clusters"][0]["cluster"]
    for account, filename in (("insighthub-day5-bot-readonly", "readonly.kubeconfig"),
                              ("insighthub-day5-scale", "scale.kubeconfig")):
        token = run(kubectl, "--context", CONTEXT, "-n", NAMESPACE,
                    "create", "token", account, "--duration=6h")
        path = STATE / filename
        path.write_text(json.dumps(kubeconfig(cluster, token, account)))
        path.chmod(0o600)
    python = str(Path(sys.executable).resolve())
    launcher = str(Path(__file__).with_name("launch.py"))
    config = {name: {"command": python, "args": [launcher, name],
                     "enabled_tools": tools,
                     "env": {key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR") if key in os.environ}}
              for name, tools in {
                  "kubernetes": ["pods_list_in_namespace", "pods_get", "pods_log", "events_list"],
                  "prometheus": ["query", "range_query"],
              }.items()}
    path = STATE / "mcp.json"
    path.write_text(json.dumps(config, indent=2) + "\n")
    path.chmod(0o600)
    print("Day 05 scoped kubeconfigs and MCP config written under ignored tmp/day5")


if __name__ == "__main__":
    main()
