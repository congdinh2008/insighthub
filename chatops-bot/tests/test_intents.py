"""Domain edge cases that could otherwise give a plausible but false answer."""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.intents import count_created_today_ready, failing_pods  # noqa: E402
from app.permissions import route  # noqa: E402


def test_ict_calendar_window_and_distinct_ids():
    now = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)
    rows = [
        {"id": 1, "status": "ready", "created_at": "2026-09-23T17:00:00Z"},
        {"id": 1, "status": "ready", "created_at": "2026-09-23T17:00:00Z"},
        {"id": 2, "status": "ready", "created_at": "2026-09-23T16:59:59Z"},
        {"id": 3, "status": "pending", "created_at": "2026-09-24T01:00:00Z"},
        {"id": 4, "status": "ready", "created_at": "2026-09-24T10:00:00Z"},
    ]
    assert count_created_today_ready(rows, now)[0] == 1


def test_count_rejects_truncated_or_invalid_data():
    now = datetime.now(UTC)
    with pytest.raises(ValueError):
        count_created_today_ready({"items": []}, now)
    with pytest.raises(ValueError):
        count_created_today_ready([{"id": 1, "status": "ready", "created_at": "2026-09-24"}], now)


def test_running_pod_with_crashloop_is_reported():
    pods = {"items": [{"metadata": {"name": "api-1"}, "status": {
        "phase": "Running", "containerStatuses": [{"ready": False,
        "state": {"waiting": {"reason": "CrashLoopBackOff"}}}]}}]}
    assert "CrashLoopBackOff" in failing_pods(pods)[0]


def test_destructive_and_out_of_range_scale_denied():
    assert route("delete namespace insighthub-dev")[0] == "destructive"
    assert route("scale api to 100")[0] == "denied"
