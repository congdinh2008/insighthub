"""A prior scan's delayed spend must not consume the next probe's tiny allowance."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/security/day6"))
import budget_settle  # noqa: E402


def test_waits_full_stability_window_after_delayed_write(monkeypatch):
    clock = [0]
    monkeypatch.setattr(budget_settle.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        budget_settle.time,
        "sleep",
        lambda seconds: clock.__setitem__(0, clock[0] + seconds),
    )
    result = budget_settle.settled_info(
        lambda: {"spend": 0.01 if clock[0] < 5 else 0.02}
    )
    assert result["spend"] == 0.02
    assert clock[0] == 17


def test_continuously_changing_spend_is_not_called_settled(monkeypatch):
    clock = [0]
    monkeypatch.setattr(budget_settle.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        budget_settle.time,
        "sleep",
        lambda seconds: clock.__setitem__(0, clock[0] + seconds),
    )
    with pytest.raises(RuntimeError, match="did not settle"):
        budget_settle.settled_info(lambda: {"spend": clock[0] * 0.01}, timeout=20)
    assert clock[0] == 20
