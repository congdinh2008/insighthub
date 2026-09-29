#!/usr/bin/env python3
"""Drain then switch API/worker together to isolated Day 06 DB, queue and virtual key."""

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from local_lab import CTX, NS, TMP, apply, kubectl, private


def main():
    keys = json.loads((TMP / "keys.json").read_text())
    infra = json.loads((TMP / "infrastructure.json").read_text())
    secret_path = TMP / "runtime-secret.json"
    if not secret_path.exists():
        deployment = json.loads(
            kubectl("get", "deployment", "insighthub-api", "-o", "json")
        )
        refs = deployment["spec"]["template"]["spec"]["containers"][0]["envFrom"]
        names = [r["secretRef"]["name"] for r in refs if "secretRef" in r]
        if len(names) != 1 or names[0].startswith("day6-"):
            raise SystemExit(
                "Cannot identify original runtime Secret; refusing inferred backup"
            )
        private(
            secret_path, json.loads(kubectl("get", "secret", names[0], "-o", "json"))
        )
    baseline = json.loads(secret_path.read_text())
    original = {k: base64.b64decode(v).decode() for k, v in baseline["data"].items()}
    with httpx.Client(timeout=15, trust_env=False) as client:
        response = client.get(
            os.environ.get("DAY6_API_URL", "http://127.0.0.1:18010") + "/documents"
        )
        response.raise_for_status()
        docs = response.json()
        if any(d["status"] == "pending" for d in docs):
            raise SystemExit("Drain incomplete: pending documents")
    values_path = TMP / "baseline-values.json"
    if not values_path.exists():
        private(
            values_path,
            json.loads(
                subprocess.check_output(
                    [
                        "helm",
                        "--kube-context",
                        CTX,
                        "-n",
                        NS,
                        "get",
                        "values",
                        "insighthub",
                        "-o",
                        "json",
                    ]
                )
            ),
        )
    old_queue = (
        json.loads(values_path.read_text())
        .get("runtime", {})
        .get("queueName", "insighthub:ingestion")
    )
    if int(kubectl("exec", "redis-0", "--", "redis-cli", "ZCARD", old_queue).strip()):
        raise SystemExit("Drain incomplete: old queue has jobs")
    env = {
        "DATABASE_URL": f"postgresql://day6:{infra['rag_password']}@day6-rag-db:5432/day6",
        "REDIS_URL": original["REDIS_URL"],
        "LITELLM_API_KEY": keys["insighthub"],
        "OPENAI_BASE_URL": "http://day6-gateway:4000/v1",
        "OPENAI_CHAT_MODEL": "app-chat",
        "OPENAI_EMBEDDING_MODEL": "app-embedding",
        "EMBEDDING_REVISION": "day6-zenlayer-text-embedding-3-large-v1",
        "SECURITY_ENABLED": "true",
        "GUARDRAIL_URL": "http://day6-guardrails:8082",
        "GUARDRAIL_API_KEY": infra["GUARD_API_KEY"],
        "LLM_MAX_TOKENS": "512",
    }
    apply(
        {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": "day6-app-runtime"},
            "stringData": env,
        }
    )
    overlay = {
        "secret": {"existingSecret": "day6-app-runtime", "createLocal": False},
        "runtime": {
            "ragMode": "real",
            "llmProvider": "openai",
            "embeddingProvider": "openai",
            "queueName": "insighthub:day6:ingestion",
            "llmInputUsdPerMillion": "0.4",
            "llmOutputUsdPerMillion": "1.6",
        },
        "images": {"api": {"tag": "day6"}, "worker": {"tag": "day6"}},
        "migration": {"enabled": False},
    }
    private(TMP / "app-values.json", overlay)
    kubectl("scale", "deployment/insighthub-ingestion-worker", "--replicas=0")
    kubectl(
        "rollout", "status", "deployment/insighthub-ingestion-worker", "--timeout=180s"
    )
    subprocess.run(
        [
            "helm",
            "--kube-context",
            CTX,
            "upgrade",
            "insighthub",
            "deploy/helm/insighthub",
            "-n",
            NS,
            "--reuse-values",
            "-f",
            str(TMP / "app-values.json"),
            "--wait",
            "--timeout",
            "5m",
        ],
        check=True,
    )
    # Keep the historical baseline isolated behind localhost port-forward only.
    baseline_env = {
        **env,
        "LITELLM_API_KEY": keys["evaluator"],
        "OPENAI_CHAT_MODEL": "eval-chat",
        "SECURITY_ENABLED": "false",
    }
    apply(
        {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": "day6-baseline-runtime"},
            "stringData": baseline_env,
        }
    )
    deployment = json.loads(
        kubectl("get", "deployment", "insighthub-api", "-o", "json")
    )
    for k in ["status"]:
        deployment.pop(k, None)
    deployment["metadata"] = {
        "name": "day6-baseline-api",
        "labels": {"day6-owner": "insighthub"},
    }
    spec = deployment["spec"]
    spec["replicas"] = 1
    spec["selector"] = {"matchLabels": {"app": "day6-baseline-api"}}
    spec["template"]["metadata"] = {
        "labels": {"app": "day6-baseline-api", "day6-owner": "insighthub"}
    }
    for ref in spec["template"]["spec"]["containers"][0]["envFrom"]:
        if "secretRef" in ref:
            ref["secretRef"]["name"] = "day6-baseline-runtime"
    apply(deployment)
    kubectl("rollout", "status", "deployment/day6-baseline-api", "--timeout=180s")
    print(
        "Day06 app isolated database/queue ready. Baseline API has no public Service."
    )


if __name__ == "__main__":
    main()
