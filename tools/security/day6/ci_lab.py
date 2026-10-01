#!/usr/bin/env python3
"""Ephemeral Compose lab for trusted CI; never uses or modifies the local kind lab."""

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[3]
TMP = ROOT / "tmp/day6"
ENV = TMP / "ci.env"
COMPOSE = [
    "docker",
    "compose",
    "-p",
    "insighthub-day6-ci",
    "--env-file",
    str(ENV),
    "-f",
    str(ROOT / "deploy/day6/compose.yaml"),
]


def write_env(values):
    if any("\n" in v or "\r" in v or "'" in v for v in values.values()):
        raise ValueError("Unsupported env value delimiter")
    fd = os.open(ENV, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("".join(k + "='" + v + "'\n" for k, v in values.items()))


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    if ENV.exists():
        raise SystemExit(
            "CI lab env already exists; use a fresh checkout instead of overwriting credentials"
        )
    values = {k: os.environ[k] for k in ("ZENLAYER_API_KEY", "ZENLAYER_BASE_URL")}
    values.update(
        DAY6_DB_PASSWORD=secrets.token_hex(24),
        DAY6_GUARD_API_KEY=secrets.token_hex(32),
        LITELLM_MASTER_KEY="sk-" + secrets.token_hex(32),
    )
    write_env(values)
    subprocess.run(
        COMPOSE
        + [
            "up",
            "--build",
            "-d",
            "--wait",
            "gateway-db",
            "rag-db",
            "redis",
            "gateway",
            "guard",
        ],
        check=True,
    )
    keys = {}
    aliases = {
        "insighthub": ("app-chat", "app-embedding"),
        "bot": ("bot-chat",),
        "coding": ("coding-chat",),
        "guard": ("guard-classifier",),
        "evaluator": ("eval-chat", "app-embedding"),
    }
    budgets = {
        "insighthub": 0.05,
        "bot": 0.01,
        "coding": 0.01,
        "guard": 0.13,
        "evaluator": 0.20,
    }
    with httpx.Client(
        base_url="http://127.0.0.1:14010",
        headers={"Authorization": "Bearer " + values["LITELLM_MASTER_KEY"]},
        timeout=60,
        trust_env=False,
    ) as client:
        for name, models in aliases.items():
            r = client.post(
                "/key/generate",
                json={
                    "key_alias": "day6-" + name,
                    "models": list(models),
                    "max_budget": budgets[name],
                    "duration": "1d",
                    "allowed_routes": ["llm_api_routes"],
                    "rpm_limit": 120,
                    "tpm_limit": 100000,
                    "max_parallel_requests": 5,
                },
            )
            r.raise_for_status()
            keys[name] = r.json()["key"]
    for filename, data in [
        ("keys.json", keys),
        ("infrastructure.json", {"LITELLM_MASTER_KEY": values["LITELLM_MASTER_KEY"]}),
    ]:
        fd = os.open(TMP / filename, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
    values.update(
        DAY6_APP_KEY=keys["insighthub"],
        DAY6_GUARD_KEY=keys["guard"],
        DAY6_EVALUATOR_KEY=keys["evaluator"],
    )
    write_env(values)
    subprocess.run(
        COMPOSE
        + ["up", "--build", "-d", "--wait", "guard", "api", "baseline", "worker"],
        check=True,
    )
    sys.path.insert(0, str(Path(__file__).parent))
    os.environ["DAY6_API_URL"] = "http://127.0.0.1:18010"
    from evaluate import upload

    with httpx.Client(timeout=120, trust_env=False) as client:
        upload(
            client, "day6-guide.md", (ROOT / "security/datasets/guide.md").read_text()
        )
    print(
        "Trusted ephemeral CI lab ready; total soft caps USD 0.40, approved envelope USD 0.50"
    )


if __name__ == "__main__":
    main()
