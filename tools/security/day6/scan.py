#!/usr/bin/env python3
"""Run Promptfoo against frozen HTTP/RAG cases, retaining raw reports and envelopes."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from evaluate import DATASET, ROOT, envelopes, now, sha, source_snapshot

parser = argparse.ArgumentParser()
parser.add_argument("profile", choices=["initial", "final"])
parser.add_argument(
    "--label", help="Separate immutable evidence folder for a replay or iteration"
)
args = parser.parse_args()
if args.label and (not args.label.replace("-", "").isalnum()):
    raise SystemExit("Use a simple alphanumeric folder label")
folder = ROOT / "docs/evidence/day6" / (args.label or args.profile)
folder.mkdir(parents=True, exist_ok=True)
ledger = folder / "results.jsonl"
if ledger.exists():
    raise SystemExit(
        "Existing scan evidence: use a new folder/version, do not overwrite"
    )
started = {
    "observed_at": now(),
    **source_snapshot(),
    "dataset_sha256": sha(DATASET.read_bytes()),
    "profile": args.profile,
}
(folder / "start.json").write_text(json.dumps(started, indent=2))
env = dict(os.environ)
env.update(
    DAY6_API_URL="http://127.0.0.1:18010",
    DAY6_TARGET_URL="http://127.0.0.1:18011"
    if args.profile == "initial"
    else "http://127.0.0.1:18010",
    DAY6_PROFILE="baseline-replay" if args.profile == "initial" else "enforced",
    DAY6_RESULT_LOG=str(ledger),
    PROMPTFOO_DISABLE_TELEMETRY="1",
    PROMPTFOO_DISABLE_REMOTE_GENERATION="true",
    PROMPTFOO_CONFIG_DIR=str(ROOT / "tmp/day6/promptfoo"),
)
# Stable paths, no shell, no secrets in argv or report config.
command = [
    str(ROOT / "security/node_modules/.bin/promptfoo"),
    "eval",
    "-c",
    "security/datasets/frozen-eval.yaml",
    "--no-cache",
    "--no-progress-bar",
    "--no-table",
    "--no-write",
    "-o",
    str(folder / "red-team-report.html"),
    "-o",
    str(folder / "promptfoo.json"),
]
r = subprocess.run(command, cwd=ROOT, env=env)
current = source_snapshot()
if (
    any(current[k] != started[k] for k in current)
    or sha(DATASET.read_bytes()) != started["dataset_sha256"]
):
    raise SystemExit(
        "INCOMPLETE: source/dataset changed during scan; raw results retained"
    )
results = (
    [json.loads(line) for line in ledger.read_text().splitlines()]
    if ledger.exists()
    else []
)
expected = {c["id"] for c in json.loads(DATASET.read_text())["cases"]}
if {x["case_id"] for x in results} != expected or len(results) != len(expected):
    raise SystemExit("INCOMPLETE: not all runtime probes returned results")
os.environ["DAY6_PROFILE"] = env["DAY6_PROFILE"]
evaluation, cost = envelopes(results)
(folder / "eval.json").write_text(json.dumps(evaluation, ensure_ascii=False, indent=2))
(folder / "cost.json").write_text(json.dumps(cost, indent=2))
print(
    json.dumps(
        {
            "profile": args.profile,
            "cases": len(results),
            "passed": sum(r["passed"] for r in results),
            "promptfoo_exit": r.returncode,
        }
    )
)
raise SystemExit(0 if args.profile == "initial" else r.returncode)
