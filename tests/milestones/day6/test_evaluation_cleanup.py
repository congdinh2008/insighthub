"""Failed uploads must not contaminate the next measured security corpus."""

import sys
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/security/day6"))
import evaluate  # noqa: E402


def test_failed_ingestion_still_deletes_exact_owned_document(monkeypatch):
    requests = []

    def respond(request):
        requests.append((request.method, request.url.path))
        if request.method == "POST":
            return httpx.Response(202, json={"id": 781, "filename": "day6-case.md"})
        if request.method == "GET":
            return httpx.Response(
                200,
                json=[{"id": 781, "status": "failed", "error_code": "provider_error"}],
            )
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(evaluate.httpx, "Client", lambda **_: client)
    with pytest.raises(RuntimeError, match="ingestion failed"):
        evaluate.run_case({"id": "case", "document": "synthetic", "input": "question"})
    assert requests[-1] == ("DELETE", "/documents/781")
    assert not any(path == "/chat" for _, path in requests)


def test_cleanup_retries_without_deleting_other_documents(monkeypatch):
    client = Mock()
    client.delete.side_effect = [
        httpx.ReadTimeout("lost response"),
        httpx.Response(404),
    ]
    monkeypatch.setattr(evaluate.time, "sleep", lambda _: None)
    evaluate.cleanup_document(client, {"id": 782, "filename": "owned.md"})
    assert client.delete.call_count == 2
    assert all(
        call.args[0].endswith("/documents/782") for call in client.delete.call_args_list
    )


def test_dirty_corpus_is_rejected_without_cleanup(monkeypatch):
    requests = []

    def respond(request):
        requests.append(request.method)
        return httpx.Response(
            200,
            json=[
                {"id": 1, "filename": "day6-guide.md", "status": "ready"},
                {"id": 2, "filename": "other.md", "status": "ready"},
            ],
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(evaluate.httpx, "Client", lambda **_: client)
    with pytest.raises(RuntimeError, match="Unexpected corpus"):
        evaluate.isolated_corpus()
    assert requests == ["GET"]
