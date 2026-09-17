"""Live Day 01 HTTP tests. Verifier executes these without root conftest/config."""

import json
import os
import time
import urllib.error
import urllib.request
import uuid

import pytest

API = os.environ.get("INSIGHTHUB_API_URL", "http://localhost:8000")
WEB = os.environ.get("INSIGHTHUB_WEB_URL", "http://localhost:3000")


def request(path, method="GET", body=None, headers=None, origin=API):
    req = urllib.request.Request(
        origin + path, data=body, headers=headers or {}, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as response:
        return response.code, response.read()


def upload(
    content=b"Day one uses a Redis queue and an independent worker.",
    filename=None,
    path="/documents",
):
    filename = filename or f"day1-{uuid.uuid4().hex}.txt"
    boundary = uuid.uuid4().hex
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: text/plain\r\n\r\n'.encode()
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )
    code, raw = request(
        path,
        "POST",
        body,
        {"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    return code, json.loads(raw)


def ready(document_id):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        code, raw = request("/documents")
        assert code == 200
        matches = [d for d in json.loads(raw) if d["id"] == document_id]
        assert len(matches) == 1
        doc = matches[0]
        assert doc["status"] != "failed", doc
        if doc["status"] == "ready":
            assert doc["chunk_count"] > 0 and doc["embedding_identity_id"]
            assert doc["error_code"] is None
            return doc
        time.sleep(0.1)
    pytest.fail(f"Document {document_id} not ready within 30s")


@pytest.fixture
def created():
    ids = []
    yield ids
    for document_id in ids:
        request(f"/documents/{document_id}", "DELETE")


def test_async_upload(created):
    started = time.monotonic()
    code, doc = upload()
    elapsed = time.monotonic() - started
    assert code == 202, doc
    created.append(doc["id"])
    assert elapsed < 1
    assert doc["status"] == "pending" and doc["chunk_count"] == 0
    assert doc["mode"] == "fixture"
    ready(doc["id"])


def test_worker_ingests(created):
    code, doc = upload()
    assert code == 202
    created.append(doc["id"])
    result = ready(doc["id"])
    assert result["filename"] == doc["filename"] and result["chunk_count"] == 1


def test_refactor_regression(created):
    content = b"Day one uses a Redis queue and an independent worker."
    code, doc = upload(content)
    assert code == 202
    created.append(doc["id"])
    ready(doc["id"])
    code, raw = request(
        "/chat",
        "POST",
        json.dumps({"question": content.decode()}).encode(),
        {"Content-Type": "application/json"},
    )
    answer = json.loads(raw)
    assert code == 200
    assert "FIXTURE" in answer["answer"]
    assert doc["filename"] in answer["sources"]
    assert any(
        c["source"] == doc["filename"]
        and c["similarity"] == 1
        and c["chunk_text"] == content.decode()
        for c in answer["contexts"]
    )
    assert answer["usage"]["source"] == "unavailable"
    assert request("/", origin=WEB)[0] == 200


def test_empty_input():
    code, result = upload(b"")
    assert code == 422 and result["code"] == "invalid_document"
    code, raw = request(
        "/chat", "POST", b'{"question":" "}', {"Content-Type": "application/json"}
    )
    assert code == 422


def test_duplicate_or_invalid(created):
    filename = f"invalid-{uuid.uuid4().hex}.txt"
    code, result = upload(b" \n ", filename)
    assert code == 422 and result["code"] == "invalid_document"
    _, raw = request("/documents")
    doc = next(d for d in json.loads(raw) if d["filename"] == filename)
    created.append(doc["id"])
    assert doc["status"] == "failed" and doc["chunk_count"] == 0
    assert upload(b"unsupported", "data.exe")[0] == 400
    assert upload(b"x" * (10 * 1024 * 1024 + 1))[0] == 413


def test_retry_idempotent(created):
    code, doc = upload()
    assert code == 202
    created.append(doc["id"])
    before = ready(doc["id"])
    for _ in range(2):
        code, result = upload(
            filename=doc["filename"], path=f"/documents/{doc['id']}/retry"
        )
        assert code == 409 and result["code"] == "document_conflict"
    after = ready(doc["id"])
    assert before == after
