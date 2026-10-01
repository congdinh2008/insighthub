"""The release runner must terminate inference work on exhausted/unknown budget."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/security/day6"))
spec = importlib.util.spec_from_file_location(
    "ci_cost_stop_test", ROOT / "tools/security/day6/ci_acceptance.py"
)
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


@pytest.mark.parametrize("cost", [0.35, None])
def test_stops_running_job_before_next_poll_when_budget_is_exhausted_or_unknown(
    monkeypatch, cost
):
    child = Mock()
    child.pid = 12345
    child.poll.return_value = None
    monkeypatch.setattr(ci.subprocess, "Popen", Mock(return_value=child))
    monkeypatch.setattr(
        ci, "ledger", lambda: [{"event": "completion", "cost_usd": cost}]
    )
    kill = Mock()
    monkeypatch.setattr(ci.os, "killpg", kill)
    with pytest.raises(RuntimeError, match="CI safety stop"):
        ci.run(["synthetic-job"])
    kill.assert_called_once_with(child.pid, ci.signal.SIGTERM)
    child.wait.assert_called_once_with(timeout=10)


def test_failed_acceptance_cannot_be_reported_as_success(monkeypatch):
    child = Mock()
    child.poll.return_value = 1
    child.returncode = 1
    monkeypatch.setattr(ci.subprocess, "Popen", Mock(return_value=child))
    with pytest.raises(RuntimeError, match="Acceptance subprocess failed: 1"):
        ci.run(["synthetic-failing-job"])


def test_historical_budget_artifact_is_not_republished_as_fresh_ci(
    monkeypatch, tmp_path
):
    historical = tmp_path / "gateway-budget.json"
    historical.write_text('{"observed_at": 1, "results": []}')
    summary = tmp_path / "ci-runtime"
    monkeypatch.setattr(ci, "EVIDENCE", tmp_path)
    monkeypatch.setattr(ci, "SUMMARY", summary)
    monkeypatch.setattr(ci, "source_snapshot", lambda: {"source_sha256": "frozen"})
    monkeypatch.setattr(ci, "ledger", lambda: [])
    invoked = []
    monkeypatch.setattr(ci, "run", lambda args, env=None: invoked.append(args))
    ci.main()
    assert historical.exists()
    assert not (summary / "gateway-budget.json").exists()
    assert "-s" in invoked[-1]
    result = json.loads((summary / "result.json").read_text())
    assert "no raw budget JSON export" in result["budget_evidence"]
