#!/usr/bin/env python3
"""Exercise the real local Prometheus budget rule, restoring the coding cap."""

import json
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent))
from gateway_tests import KEYS, info, update
from local_lab import ROOT


def state(client):
    response = client.get(
        os.environ.get("DAY6_PROMETHEUS_URL", "http://127.0.0.1:19090")
        + "/api/v1/alerts"
    )
    response.raise_for_status()
    return [
        a
        for a in response.json()["data"]["alerts"]
        if a["labels"].get("alertname") == "Day6KeyBudgetNearLimit"
        and a["labels"].get("workload") == "coding-workflow"
    ]


def main():
    key = KEYS["coding"]
    before = info(key)
    assert before["spend"] > 0
    samples = []
    with httpx.Client(timeout=10, trust_env=False) as client:
        assert not state(client), "Coding budget alert must start resolved"
        try:
            update(key, before["spend"] / 0.85)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                alerts = state(client)
                samples.append({"observed_at": time.time(), "alerts": alerts})
                if any(a["state"] == "firing" for a in alerts):
                    break
                time.sleep(5)
            else:
                raise RuntimeError("Budget alert did not fire")
        finally:
            update(key, before["max_budget"])
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            alerts = state(client)
            samples.append({"observed_at": time.time(), "alerts": alerts})
            if not alerts:
                break
            time.sleep(5)
        else:
            raise RuntimeError("Budget alert did not resolve after cap restoration")
    result = {
        "observed_at": time.time(),
        "status": "PASS",
        "workload": "coding-workflow",
        "original_cap": before["max_budget"],
        "test_cap": before["spend"] / 0.85,
        "restored_cap": info(key)["max_budget"],
        "samples": samples,
        "notification_delivery": "Not requested; rule firing/resolved only",
    }
    (ROOT / "docs/evidence/day6/budget-alert.json").write_text(
        json.dumps(result, indent=2)
    )
    print("PASS: real Prometheus budget alert fired and resolved; cap restored")


if __name__ == "__main__":
    main()
