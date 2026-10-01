#!/usr/bin/env python3
"""45-second budget fault for Computer Use; always restores the original cap."""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gateway_tests import KEYS, chat, info, update
from local_lab import ROOT

parser = argparse.ArgumentParser()
parser.add_argument("workload", choices=["insighthub", "bot"])
args = parser.parse_args()
key = KEYS[args.workload]
before = info(key)
result = {
    "observed_at": time.time(),
    "workload": args.workload,
    "original_cap": before["max_budget"],
    "spend_before": before["spend"],
}
assert before["spend"] > 0
try:
    update(key, max(before["spend"] / 2, 0.000001))
    denied = chat(args.workload)
    assert denied.status_code in (400, 402, 429) and "budget" in denied.text.lower()
    result["denied_status"] = denied.status_code
    print("BUDGET FAULT ACTIVE " + args.workload, flush=True)
    time.sleep(45)
finally:
    update(key, before["max_budget"])
    print("BUDGET RESTORED " + args.workload, flush=True)
after = chat(args.workload)
assert after.status_code == 200
result["recovered_status"] = after.status_code
(ROOT / "docs/evidence/day6" / ("ui-budget-" + args.workload + ".json")).write_text(
    json.dumps(result, indent=2)
)
