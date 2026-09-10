"""Student Day 1 runtime contract tests; the verifier supplies local URLs."""

import json
import os
import time
import urllib.error
import urllib.request
import uuid


def api_url() -> str:
    value = os.environ.get("INSIGHTHUB_API_URL")
    assert value, "INSIGHTHUB_API_URL is required for Day 1 runtime tests"
    return value.rstrip("/")


def request(path: str, body: bytes | None = None, content_type: str = "application/json"):
    req = urllib.request.Request(
        api_url() + path, body, headers={"Content-Type": content_type}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


def upload(content: bytes, suffix: str = "txt"):
    boundary = "Day1" + uuid.uuid4().hex
    filename = "day1-contract-" + uuid.uuid4().hex + "." + suffix
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: text/plain\r\n\r\n"
        ).encode()
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return request("/documents", body, f"multipart/form-data; boundary={boundary}")


def document(document_id: int, expected: set[str]):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        status, docs = request("/documents")
        assert status == 200
        matches = [doc for doc in docs if doc["id"] == document_id]
        assert len(matches) == 1
        if matches[0]["status"] in expected:
            return matches[0]
        time.sleep(0.1)
    raise AssertionError("document did not reach expected state")


def test_async_upload():
    status, accepted = upload(b"Day 1 async contract upload.")
    assert status == 202
    assert accepted["status"] == "pending"


def test_worker_ingests():
    status, accepted = upload(b"Worker must store this unique contract document.")
    assert status == 202
    ready = document(accepted["id"], {"ready"})
    assert ready["chunk_count"] > 0


def test_empty_input():
    status, rejected = upload(b"")
    assert status == 422
    assert rejected["code"] == "invalid_document"


def test_duplicate_or_invalid():
    # The contract does not promise deduplication across separate uploads. An
    # unsupported extension must instead be rejected before a job is admitted.
    status, rejected = upload(b"not executable", suffix="exe")
    assert status == 400
    assert "Chỉ chấp nhận" in rejected["detail"]


def test_refactor_regression():
    live_status, live = request("/healthz")
    ready_status, ready = request("/readyz")
    assert live_status == 200 and live["status"] == "ok"
    assert ready_status == 200 and ready["status"] == "ready" and ready["db"] is True

    content = b"Refactor regression document remains retrievable by chat."
    status, accepted = upload(content)
    assert status == 202 and accepted["status"] == "pending"
    stored = document(accepted["id"], {"ready"})
    assert stored["chunk_count"] > 0
    chat_status, chat = request("/chat", json.dumps({"question": content.decode()}).encode())
    assert chat_status == 200
    assert stored["filename"] in chat["sources"]
    assert any(context["source"] == stored["filename"] for context in chat["contexts"])


def test_retry_idempotent():
    # Whitespace passes upload validation and fails only in the worker, safely.
    status, accepted = upload(b" \n\t ")
    assert status == 202
    failed = document(accepted["id"], {"failed"})
    assert failed["chunk_count"] == 0
    retry_status, retry = request(f"/documents/{accepted['id']}/retry", b"{}")
    assert retry_status == 202
    assert retry["id"] == accepted["id"]
    failed_again = document(accepted["id"], {"failed"})
    assert failed_again["chunk_count"] == 0
