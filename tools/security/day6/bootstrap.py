#!/usr/bin/env python3
"""Create least-privilege keys and install the service classifier identity."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from local_lab import TMP, apply, kubectl, private

WORKLOADS = {
    "insighthub": ("day6-insighthub", ["app-chat", "app-embedding"], 1.5),
    "bot": ("day6-bot", ["bot-chat"], 0.5),
    "coding": ("day6-coding", ["coding-chat"], 1.0),
    "guard": ("day6-guard", ["guard-classifier"], 1.0),
    "evaluator": ("day6-evaluator", ["eval-chat", "app-embedding"], 0.5),
}


def main():
    infrastructure = json.loads((TMP / "infrastructure.json").read_text())
    path = TMP / "keys.json"
    keys = json.loads(path.read_text()) if path.exists() else {}
    base = os.environ.get("DAY6_GATEWAY_URL", "http://127.0.0.1:14010")
    with httpx.Client(
        base_url=base,
        timeout=30,
        trust_env=False,
        headers={"Authorization": "Bearer " + infrastructure["LITELLM_MASTER_KEY"]},
    ) as client:
        health = client.get("/health/liveliness")
        health.raise_for_status()
        for workload, (alias, models, budget) in WORKLOADS.items():
            if workload in keys:
                continue
            response = client.post(
                "/key/generate",
                json={
                    "key_alias": alias,
                    "models": models,
                    "max_budget": budget,
                    "duration": "7d",
                    "key_type": "llm_api",
                    "max_parallel_requests": 5,
                    "rpm_limit": 120,
                    "tpm_limit": 100000,
                    "metadata": {"owner": "insighthub-day6", "workload": workload},
                },
            )
            if response.status_code != 200:
                raise SystemExit(
                    f"Key bootstrap failed: {workload}, status {response.status_code}"
                )
            data = response.json()
            keys[workload] = data["key"]
            private(path, keys)
            print(
                workload,
                "created",
                {"max_budget": budget, "models": models, "key_type": "llm_api"},
            )
    apply(
        {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": "day6-classifier"},
            "stringData": {
                "GUARD_MODEL_KEY": keys["guard"],
                "GUARD_MODEL_URL": "http://day6-gateway:4000/v1",
            },
        }
    )
    patch = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {
                            "name": "day6-guardrails",
                            "envFrom": [{"secretRef": {"name": "day6-classifier"}}],
                        }
                    ]
                }
            }
        }
    }
    kubectl(
        "patch",
        "deployment",
        "day6-guardrails",
        "--type=strategic",
        "-p",
        json.dumps(patch),
    )
    kubectl("rollout", "status", "deployment/day6-guardrails", "--timeout=180s")
    print(
        "Classifier routes through its restricted gateway key. Credentials saved only in ignored private file."
    )


if __name__ == "__main__":
    main()
