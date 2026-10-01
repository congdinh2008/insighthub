"""Incomplete paid attempts must remain visible instead of looking like zero cost."""

import asyncio
import importlib.util
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "day6_exporter_test", ROOT / "gateway/exporter.py"
)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


@pytest.mark.parametrize("native_available", [True, False])
def test_unknown_cost_includes_old_admissions_but_not_pending_or_completed(
    tmp_path, monkeypatch, native_available
):
    now = time.time()
    rows = [
        {
            "event": "admitted",
            "request_id": "lost",
            "workload": "evaluator",
            "timestamp": now - 121,
        },
        {
            "event": "upstream_failure",
            "request_id": "lost",
            "workload": "evaluator",
            "cost_usd": None,
        },
        {
            "event": "upstream_failure",
            "request_id": "lost",
            "workload": "evaluator",
            "cost_usd": None,
        },
        {
            "event": "admitted",
            "request_id": "pending",
            "workload": "evaluator",
            "timestamp": now - 10,
        },
        {
            "event": "admitted",
            "request_id": "done",
            "workload": "evaluator",
            "timestamp": now - 121,
        },
        {
            "event": "completion",
            "request_id": "done",
            "workload": "evaluator",
            "cost_usd": 0.125,
        },
        {
            "event": "completion",
            "request_id": "unknown",
            "workload": "evaluator",
            "cost_usd": None,
        },
        {
            "event": "upstream_failure",
            "request_id": None,
            "workload": "evaluator",
            "cost_usd": None,
        },
    ]
    path = tmp_path / "ledger.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setenv("DAY6_AUDIT_PATH", str(path))
    monkeypatch.setenv("LITELLM_MASTER_KEY", "synthetic-test-key")
    client = AsyncMock()
    if native_available:
        client.get.return_value = exporter.httpx.Response(
            200,
            json={"keys": [{"max_budget": 1.0, "spend": 0.1}]},
            request=exporter.httpx.Request("GET", "http://gateway/key/list"),
        )
    else:
        client.get.side_effect = exporter.httpx.ConnectError("unavailable")
    factory = AsyncMock()
    factory.__aenter__.return_value = client
    monkeypatch.setattr(exporter.httpx, "AsyncClient", lambda **kwargs: factory)
    response = asyncio.run(exporter.metrics())
    body = response.body.decode()
    assert 'day6_llm_unknown_cost_total{workload="evaluator"} 2.0' in body
    assert 'day6_llm_spend_usd_total{workload="evaluator"} 0.125' in body
    assert f"day6_accounting_available {1.0 if native_available else 0.0}" in body
