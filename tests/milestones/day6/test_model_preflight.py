"""An expired upstream key must stop a bulk scan despite healthy containers."""

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/security/day6"))
import evaluate  # noqa: E402


@pytest.mark.parametrize(
    "status,body,error",
    [
        (503, {"error": "guardrail_unavailable"}, "HTTP 503"),
        (429, {"error": "budget_exceeded"}, "HTTP 429"),
        (200, {"answer": "PostgreSQL", "sources": []}, "grounded guide fact"),
        (200, {"answer": "unrelated", "sources": ["guide"]}, "grounded guide fact"),
    ],
)
def test_broken_model_path_stops_preflight(monkeypatch, status, body, error):
    client = httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(status, json=body))
    )
    monkeypatch.setattr(evaluate.httpx, "Client", lambda **_: client)
    with pytest.raises(RuntimeError, match=error):
        evaluate.model_preflight("http://local-test")


def test_preflight_records_only_metadata_after_grounded_response(monkeypatch):
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={"answer": "PostgreSQL with pgvector", "sources": ["guide"]},
                headers={"x-request-id": "synthetic-request-id"},
            )
        )
    )
    monkeypatch.setattr(evaluate.httpx, "Client", lambda **_: client)
    result = evaluate.model_preflight("http://local-test")
    assert result["status"] == 200
    assert result["request_id"] == "synthetic-request-id"
    assert "answer" not in result and "sources" not in result
