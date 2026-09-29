#!/usr/bin/env python3
"""Scoped faults with restoration; execute only after scans are idle."""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from gateway_tests import KEYS, info
from local_lab import ROOT, kubectl

API = "http://127.0.0.1:18010"
TARGETS = {
    "guard": ("deployment/day6-guardrails", "guardrail_unavailable"),
    "gateway": ("deployment/day6-gateway", "guardrail_unavailable"),
    "accounting-db": ("statefulset/day6-gateway-db", "guardrail_unavailable"),
}


def probe():
    with httpx.Client(timeout=75, trust_env=False) as client:
        start = time.monotonic()
        r = client.post(
            API + "/chat",
            json={"question": "Which database stores vectors?", "top_k": 1},
        )
        return {
            "status": r.status_code,
            "code": r.json().get("code"),
            "duration_seconds": time.monotonic() - start,
            "request_id": r.headers.get("x-request-id"),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fault", choices=list(TARGETS))
    parser.add_argument(
        "--hold-ui",
        action="store_true",
        help="45 seconds for Computer Use, then automatic restore",
    )
    args = parser.parse_args()
    target, code = TARGETS[args.fault]
    before = json.loads(kubectl("get", target, "-o", "json"))
    replicas = before["spec"]["replicas"]
    assert replicas == 1, "Unexpected original replicas; refusing mutation"
    result = {
        "fault": args.fault,
        "target": target,
        "observed_at": time.time(),
        "original_replicas": replicas,
    }
    before_keys = {name: info(key) for name, key in KEYS.items()}
    try:
        kubectl("scale", target, "--replicas=0")
        kubectl("rollout", "status", target, "--timeout=120s")
        # StatefulSet scale-to-zero readiness alone can complete before termination.
        selector = before["spec"]["selector"]["matchLabels"]
        labels = ",".join(k + "=" + v for k, v in selector.items())
        deadline = time.monotonic() + 120
        while json.loads(kubectl("get", "pods", "-l", labels, "-o", "json"))["items"]:
            if time.monotonic() > deadline:
                raise RuntimeError("Pod termination timeout")
            time.sleep(1)
        print("FAULT ACTIVE " + args.fault, flush=True)
        if args.hold_ui:
            time.sleep(45)
        result["during"] = probe()
        assert result["during"]["status"] == 503 and result["during"]["code"] == code, (
            result["during"]
        )
    finally:
        kubectl("scale", target, "--replicas=" + str(replicas))
        kubectl("rollout", "status", target, "--timeout=300s")
        result["restored_replicas"] = replicas
        print("RESTORED " + args.fault, flush=True)
    recovery = []
    deadline = time.monotonic() + 90
    while True:
        try:
            attempt = probe()
        except httpx.HTTPError as exc:
            attempt = {"status": None, "error_type": type(exc).__name__}
        recovery.append(attempt)
        if attempt["status"] == 200 or time.monotonic() >= deadline:
            break
        time.sleep(2)
    result["recovery_attempts"] = recovery
    result["after"] = recovery[-1]
    assert result["after"]["status"] == 200, result["after"]
    for attempt in range(4):
        try:
            after_keys = {name: info(key) for name, key in KEYS.items()}
            break
        except httpx.HTTPError:
            if attempt == 3:
                raise
            time.sleep(2)
    result["persistent_keys"] = {}
    for name, before_key in before_keys.items():
        after_key = after_keys[name]
        assert after_key["spend"] >= before_key["spend"]
        assert after_key["max_budget"] == before_key["max_budget"]
        assert after_key["models"] == before_key["models"]
        result["persistent_keys"][name] = {
            "spend_before": before_key["spend"],
            "spend_after": after_key["spend"],
            "max_budget": after_key["max_budget"],
            "model_acl_unchanged": True,
        }
    dest = ROOT / "docs/evidence/day6" / ("fault-" + args.fault + ".json")
    dest.write_text(json.dumps(result, indent=2))
    print(dest)


if __name__ == "__main__":
    main()
