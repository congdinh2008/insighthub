#!/usr/bin/env python3
"""Actual expiry, revocation and key-isolation probes; ephemeral keys are removed."""

import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gateway_tests import KEYS, MASTER, call, chat, info, update
from local_lab import ROOT


def main():
    rows = []
    missing = call(
        "",
        "/v1/chat/completions",
        {"model": "app-chat", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert missing.status_code in (401, 403)
    rows.append({"probe": "missing-key", "status": missing.status_code})
    for mode in ("expiry", "revocation"):
        created = call(
            MASTER,
            "/key/generate",
            {
                "key_alias": "day6-auth-probe-" + uuid.uuid4().hex,
                "models": ["app-chat"],
                "max_budget": 0.01,
                "duration": "5s" if mode == "expiry" else "5m",
                "allowed_routes": ["llm_api_routes"],
            },
        )
        created.raise_for_status()
        key = created.json()["key"]
        try:
            # Native authenticated catalog route exercises key validity without a
            # fourth workload identity, paid generation, or key-alias collisions.
            allowed = call(key, "/v1/models", method="GET")
            assert allowed.status_code == 200, allowed.status_code
            start = time.monotonic()
            if mode == "expiry":
                time.sleep(6)
            else:
                deleted = call(MASTER, "/key/delete", {"keys": [key]})
                deleted.raise_for_status()
            denied = call(key, "/v1/models", method="GET")
            assert denied.status_code in (401, 403), denied.status_code
            rows.append(
                {
                    "probe": mode,
                    "allowed_status": allowed.status_code,
                    "denied_status": denied.status_code,
                    "elapsed_seconds": time.monotonic() - start,
                    "route": "/v1/models",
                    "scope": "native authentication; real generation is proven separately for all three workload keys",
                }
            )
        finally:
            call(MASTER, "/key/delete", {"keys": [key]})
    original = info(KEYS["insighthub"])["max_budget"]
    try:
        spend = info(KEYS["insighthub"])["spend"]
        update(KEYS["insighthub"], max(spend / 2, 0.000001))
        denied = chat("insighthub")
        unaffected = chat("bot")
        assert denied.status_code in (400, 402, 429) and "budget" in denied.text.lower()
        assert unaffected.status_code == 200
        rows.append(
            {
                "probe": "key-budget-isolation",
                "exhausted_status": denied.status_code,
                "other_workload_status": unaffected.status_code,
            }
        )
    finally:
        update(KEYS["insighthub"], original)
    (ROOT / "docs/evidence/day6/key-lifecycle.json").write_text(
        json.dumps({"observed_at": time.time(), "results": rows}, indent=2)
    )
    print("Missing, expired, revoked and independently budgeted keys verified")


if __name__ == "__main__":
    main()
