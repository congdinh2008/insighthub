#!/usr/bin/env python3
"""One approved CI replay, with cost monitoring and immutable evidence per stage."""

import json
import os
import signal
import subprocess
import sys
import time

from ci_lab import COMPOSE, ROOT
from evaluate import source_snapshot

EVIDENCE = ROOT / "docs/evidence/day6"
SUMMARY = EVIDENCE / "ci-runtime"


def ledger():
    raw = subprocess.check_output(
        COMPOSE + ["exec", "-T", "gateway", "cat", "/ledger/audit.jsonl"], text=True
    )
    return [json.loads(line) for line in raw.splitlines()]


def known_cost(rows):
    return sum(
        row["cost_usd"]
        for row in rows
        if row["event"] == "completion"
        and isinstance(row.get("cost_usd"), (float, int))
    )


def stop_child(child):
    if child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()


def run(args, env=None):
    child = subprocess.Popen(args, env=env, start_new_session=True)
    try:
        while child.poll() is None:
            rows = ledger()
            # Reserve USD 0.15 for bounded in-flight work and asynchronous writes.
            if known_cost(rows) >= 0.35 or any(
                r["event"] == "completion"
                and not isinstance(r.get("cost_usd"), (float, int))
                for r in rows
            ):
                raise RuntimeError("CI safety stop: budget reserve or missing usage")
            time.sleep(2)
        if child.returncode:
            raise RuntimeError(f"Acceptance subprocess failed: {child.returncode}")
    finally:
        stop_child(child)


def main():
    SUMMARY.mkdir(parents=True, exist_ok=False)
    frozen = source_snapshot()
    report = {
        "source": frozen,
        "approved_envelope_usd": 0.5,
        "soft_caps_total_usd": 0.4,
        "watchdog_stop_usd": 0.35,
        "status": "INCOMPLETE",
    }
    try:
        run(
            [
                sys.executable,
                "tools/security/day6/scan.py",
                "initial",
                "--label",
                "ci-baseline",
            ]
        )
        run(
            [
                sys.executable,
                "tools/security/day6/scan.py",
                "final",
                "--label",
                "ci-final",
            ]
        )
        env = dict(
            os.environ,
            DAY6_LIVE="1",
            DAY6_RESULT_LOG=str(SUMMARY / "live-results.jsonl"),
        )
        run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/milestones/day6",
                "-q",
                "--junitxml",
                str(SUMMARY / "junit.xml"),
            ],
            env,
        )
        assert source_snapshot() == frozen, "Source changed during acceptance"
        report["status"] = "PASS"
    finally:
        rows = ledger()
        report["known_cost_usd"] = known_cost(rows)
        report["within_approved_envelope"] = report["known_cost_usd"] < 0.5
        if not report["within_approved_envelope"]:
            report["status"] = "FAIL"
        admitted = {r["request_id"] for r in rows if r["event"] == "admitted"}
        completed = {r["request_id"] for r in rows if r["event"] == "completion"}
        report["unresolved_admissions"] = sorted(admitted - completed)
        report["observed_at"] = time.time()
        (SUMMARY / "ledger.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows)
        )
        (SUMMARY / "result.json").write_text(json.dumps(report, indent=2))
        budget = EVIDENCE / "gateway-budget.json"
        if budget.exists():
            (SUMMARY / "gateway-budget.json").write_bytes(budget.read_bytes())
        print(json.dumps(report), flush=True)
    assert report["known_cost_usd"] < 0.5, "Approved CI envelope exceeded"


if __name__ == "__main__":
    main()
