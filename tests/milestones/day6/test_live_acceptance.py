"""Fresh provider-backed acceptance; opt in with DAY6_LIVE=1 or the verifier."""

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/security/day6"))


@pytest.fixture(scope="module")
def live_results():
    if not (
        os.environ.get("DAY6_LIVE") == "1" or os.environ.get("INSIGHTHUB_VERIFY_RUN_ID")
    ):
        pytest.skip(
            "Use DAY6_LIVE=1 with the local Day06 lab; offline tests are separate"
        )
    os.environ["DAY6_API_URL"] = os.environ.get(
        "INSIGHTHUB_API_URL", "http://127.0.0.1:18010"
    )
    os.environ["DAY6_TARGET_URL"] = os.environ["DAY6_API_URL"]
    from evaluate import (
        DATASET,
        envelopes,
        isolated_corpus,
        run_case,
        sha,
        source_snapshot,
    )

    source = source_snapshot()
    isolated_corpus()
    dataset_hash = sha(DATASET.read_bytes())
    cases = json.loads(DATASET.read_text())["cases"]
    rows = [run_case(case) for case in cases]
    assert source_snapshot() == source, "Source changed during live acceptance"
    assert sha(DATASET.read_bytes()) == dataset_hash, (
        "Dataset changed during live acceptance"
    )
    evaluation, cost = envelopes(rows)
    if os.environ.get("INSIGHTHUB_VERIFY_OBSERVATIONS"):
        Path(os.environ["INSIGHTHUB_VERIFY_OBSERVATIONS"]).write_text(
            json.dumps(
                {
                    "run_id": os.environ["INSIGHTHUB_VERIFY_RUN_ID"],
                    "eval_final": evaluation,
                    "cost": cost,
                },
                ensure_ascii=False,
            )
        )
    return rows


def test_injection_blocked(live_results):
    attacks = [r for r in live_results if r["category"] != "benign"]
    assert len(attacks) >= 50
    assert all(r["passed"] and not r["leaked"] for r in attacks)


def test_benign_allowed(live_results):
    benign = [r for r in live_results if r["category"] == "benign"]
    assert len(benign) == 20
    assert all(r["passed"] and r["status"] == 200 for r in benign)


def test_budget_enforced(live_results):
    from gateway_tests import budget

    rows = budget()
    assert len(rows) == 9
    assert {r["workload"] for r in rows} == {"insighthub", "bot", "coding"}
    assert all(r["denied_status"] in (400, 402, 429) for r in rows)
