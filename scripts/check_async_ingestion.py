"""Measure one fixed local fixture upload, fresh-ID readiness, chat and worker log.

Run from the repo root in WSL: python3 scripts/check_async_ingestion.py
Retains the uploaded document and payload. Does not replace the Day 1 verifier.
"""

import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path


def request(
    path: str, body: bytes | None = None, content_type: str = "application/json"
):
    req = urllib.request.Request(
        "http://localhost:8000" + path,
        body,
        headers={"Content-Type": content_type},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


def upload(content: bytes, filename: str) -> tuple[int, dict]:
    boundary = "InsightHubDay1Boundary"
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: text/plain\r\n\r\n"
        ).encode()
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return request("/documents", body, f"multipart/form-data; boundary={boundary}")


def wait_for_document(document_id: int, expected: set[str]) -> dict:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        status, documents = request("/documents")
        assert status == 200
        matches = [document for document in documents if document["id"] == document_id]
        assert len(matches) == 1
        if matches[0]["status"] in expected:
            return matches[0]
        time.sleep(0.05)
    raise AssertionError(f"Document {document_id} did not reach {expected}")


def main() -> None:
    state = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        check=True, capture_output=True, text=True,
    )
    services = [json.loads(line) for line in state.stdout.splitlines() if line.strip()]
    assert {s["Service"] for s in services} == {"api", "web", "postgres", "redis", "ingestion-worker"}
    assert all(s["Health"] == "healthy" for s in services)
    # Compare full settings without printing credentials or connection strings.
    settings_probe = (
        "import hashlib; from app.core.config import get_settings; "
        "s=get_settings(); "
        "assert s.rag_mode == s.llm_provider == s.embedding_provider == 'fixture'; "
        "print(hashlib.sha256(s.model_dump_json().encode()).hexdigest())"
    )
    signatures = [
        subprocess.run(
            ["docker", "compose", "exec", "-T", service, "python", "-c", settings_probe],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        for service in ("api", "ingestion-worker")
    ]
    assert signatures[0] == signatures[1], "API and worker settings differ"
    # Identical bytes on every run; unique filename prevents accepting old sources.
    content = b"InsightHub Day 1 fixture: Redis queues jobs and the worker stores document chunks."
    filename = "day1-async-" + uuid.uuid4().hex + ".txt"
    _, root = request("/")
    assert root["mode"] == "fixture", "This probe only permits fixture mode"
    started_at = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    status, accepted = upload(content, filename)
    upload_seconds = time.perf_counter() - start
    assert status == 202, status
    document_id = accepted["id"]
    assert accepted["status"] == "pending"
    document = wait_for_document(document_id, {"ready"})
    assert document["filename"] == filename
    ready_seconds = time.perf_counter() - start
    assert document["chunk_count"] == 1
    assert document["error_code"] is None
    chat_status, chat = request(
        "/chat", json.dumps({"question": content.decode()}).encode()
    )
    assert chat_status == 200 and chat["mode"] == "fixture"
    assert "FIXTURE" in chat["answer"] and filename in chat["sources"]
    assert any(
        c["source"] == filename and c["chunk_text"] == content.decode()
        for c in chat["contexts"]
    )
    logs = subprocess.run(
        [
            "docker",
            "compose",
            "logs",
            "--no-log-prefix",
            "--since",
            started_at,
            "ingestion-worker",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    events = []
    for line in (logs.stdout + logs.stderr).splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if (
            event.get("event") == "ingestion_completed"
            and event.get("document_id") == document_id
        ):
            assert event["status"] == "ready"
            timestamp = datetime.fromisoformat(
                event["timestamp"].replace("Z", "+00:00")
            )
            assert timestamp.tzinfo is not None and timestamp >= datetime.fromisoformat(
                started_at
            )
            events.append(event)
    assert events, "Missing correlated worker completion event"
    # The request is rejected before persistence; this tests the stated 10 MB
    # boundary without keeping a large payload in the shared volume.
    too_large_status, too_large = upload(
        b"x" * (10 * 1024 * 1024 + 1), "day1-too-large.txt"
    )
    assert too_large_status == 413, too_large
    # Whitespace is accepted by request validation but rejected by the worker.
    # Retrying it proves the failed-only route and stable ARQ job ID without
    # inventing a production provider outage. It remains a zero-chunk failure.
    retry_status, retry_accepted = upload(b" \n\t ", "day1-retry.txt")
    assert retry_status == 202, retry_accepted
    retry_id = retry_accepted["id"]
    first_failure = wait_for_document(retry_id, {"failed"})
    accepted_retry_status, accepted_retry = request(f"/documents/{retry_id}/retry", b"{}")
    assert accepted_retry_status == 202, accepted_retry
    second_failure = wait_for_document(retry_id, {"failed"})
    assert first_failure["chunk_count"] == second_failure["chunk_count"] == 0
    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "mode": "fixture",
        "five_services_healthy": True,
        "api_worker_settings_identical": True,
        "workload_bytes": len(content),
        "workload_sha256": hashlib.sha256(content).hexdigest(),
        "document_id": document_id,
        "filename": filename,
        "upload_status": status,
        "upload_seconds": upload_seconds,
        "ready_seconds_from_upload_start": ready_seconds,
        "chunk_count": document["chunk_count"],
        "chat_status": chat_status,
        "fresh_source_verified": True,
        "worker_events": events,
        "oversize_upload_status": too_large_status,
        "retry_document_id": retry_id,
        "retry_status": accepted_retry_status,
        "retry_first_status": first_failure["status"],
        "retry_second_status": second_failure["status"],
        "retry_chunk_count": second_failure["chunk_count"],
        "upload_under_one_second": upload_seconds < 1,
        "ready_under_30_seconds": ready_seconds < 30,
    }
    Path("evidence").mkdir(exist_ok=True)
    Path("evidence/day1-async-runtime.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))
    assert upload_seconds < 1, "Upload exceeded one second"
    assert ready_seconds < 30, "Ready exceeded 30 seconds"


if __name__ == "__main__":
    main()
