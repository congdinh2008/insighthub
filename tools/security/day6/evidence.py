#!/usr/bin/env python3
"""Snapshot sanitized runtime/config and reconcile durable native accounting."""

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evaluate import fingerprint
from gateway_tests import KEYS, info
from local_lab import ROOT, kubectl


def snapshot(folder):
    folder.mkdir(parents=True, exist_ok=True)
    pods = json.loads(kubectl("get", "pods", "-o", "json"))["items"]
    runtime = []
    for pod in pods:
        name = pod["metadata"]["name"]
        if name.startswith(
            ("day6-", "insighthub-api-", "insighthub-ingestion-worker-")
        ):
            runtime.append(
                {
                    "pod": name,
                    "containers": [
                        {
                            "name": c["name"],
                            "image": c["image"],
                            "image_id": c["imageID"],
                            "ready": c["ready"],
                        }
                        for c in pod.get("status", {}).get("containerStatuses", [])
                    ],
                }
            )
    hashes = {}
    for group in ("gateway", "security/guardrails", "api/app", "tools/security/day6"):
        for path in sorted((ROOT / group).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                hashes[str(path.relative_to(ROOT))] = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
    code = """import json,os
from app.core.config import get_settings
s=get_settings()
print(json.dumps({"security_enabled":s.security_enabled,"gateway_url":s.openai_base_url,"chat_model":s.resolved_chat_model,"embedding":s.embedding_identity,"index_identity":s.embedding_identity_id,"queue":s.queue_name,"virtual_key_present":bool(s.litellm_api_key),"upstream_key_absent":not any(os.environ.get(k) for k in ["ZENLAYER_API_KEY","GEMINI_API_KEY","ANTHROPIC_API_KEY","LITELLM_MASTER_KEY"])}))"""
    application = json.loads(
        kubectl("exec", "deployment/insighthub-api", "--", "python", "-c", code)
    )
    (folder / "manifest.json").write_text(
        json.dumps(
            {
                "observed_at": time.time(),
                "aws_used": False,
                "source_sha256": fingerprint(ROOT),
                "file_sha256": hashes,
                "runtime": runtime,
                "application": application,
            },
            indent=2,
        )
    )
    # Only our hook's allowlisted metadata, never generic provider access logs.
    ledger = kubectl(
        "exec",
        "deployment/day6-gateway",
        "-c",
        "day6-gateway",
        "--",
        "cat",
        "/ledger/audit.jsonl",
    )
    rows = [json.loads(line) for line in ledger.splitlines()]
    allowed = {
        "timestamp",
        "event",
        "request_id",
        "provider_request_id",
        "run_id",
        "parent_request_id",
        "workload",
        "model",
        "provider",
        "input_tokens",
        "output_tokens",
        "cached_tokens",
        "cost_usd",
        "duration_seconds",
        "reason",
        "phase",
        "model_alias",
        "operation",
        "policy_mode",
    }
    assert all(set(row) <= allowed for row in rows)
    (folder / "gateway-ledger.jsonl").write_text(ledger)
    spend = defaultdict(float)
    cached = Counter()
    unknown = Counter()
    events = Counter()
    for row in rows:
        w = row.get("workload", "unknown")
        events[(w, row["event"])] += 1
        if row["event"] == "completion":
            cost = row.get("cost_usd")
            if isinstance(cost, (float, int)):
                spend[w] += cost
            else:
                unknown[w] += 1
            cached[w] += row.get("cached_tokens", 0) or 0
    aliases = {
        "insighthub": "insighthub",
        "bot": "chatops-bot",
        "coding": "coding-workflow",
        "guard": "guardrail",
        "evaluator": "evaluator",
    }
    accounting = {}
    for key, label in aliases.items():
        native = info(KEYS[key])
        accounting[label] = {
            "native_spend_usd": native["spend"],
            "ledger_spend_usd": spend[label],
            "delta_usd": spend[label] - native["spend"],
            "max_budget_usd": native["max_budget"],
            "models": native["models"],
            "expires": native["expires"],
            "cached_input_tokens": cached[label],
            "unknown_completions": unknown[label],
        }
    final = {
        "observed_at": time.time(),
        "currency": "USD",
        "pricing_source": "ZenLayer catalog 2026-09-29, not an invoice",
        "source_sha256": fingerprint(ROOT),
        "total_ledger_usd": sum(spend.values()),
        "keys": accounting,
        "events": [
            {"workload": w, "event": e, "count": n} for (w, e), n in events.items()
        ],
        "scope": "All gateway calls since lab bootstrap, including generator, baseline, classifier, ingestion, failed-then-retried coding and output-denied completions. Subscription usage is separate.",
    }
    (folder / "cost-reconciliation.json").write_text(json.dumps(final, indent=2))
    print(
        json.dumps(
            {
                "total_ledger_usd": final["total_ledger_usd"],
                "accounting_deltas": {k: v["delta_usd"] for k, v in accounting.items()},
                "unknown_completions": dict(unknown),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", default="docs/evidence/day6/runtime")
    args = parser.parse_args()
    snapshot(ROOT / args.folder)
