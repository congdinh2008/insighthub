"""Explicit lab-only latency, persistence, SIGTERM and redelivery acceptance probe.

Run separately from the verifier: this intentionally stops ONLY its named lab worker/Redis.
"""

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from test_contract import ready, request, upload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert args.project.startswith("insighthub-"), (
        "Use an isolated InsightHub lab project"
    )
    compose = ["docker", "compose", "--project-name", args.project]
    ids = []
    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "project": args.project,
        "api_url": os.environ["INSIGHTHUB_API_URL"],
        "mode": "fixture",
        "aws_used": False,
    }

    def run(*command, data=None):
        return subprocess.run(
            compose + list(command),
            input=data,
            capture_output=True,
            check=True,
            timeout=170,
        ).stdout.decode()

    def events():
        lines = run(
            "logs", "--no-color", "--no-log-prefix", "ingestion-worker"
        ).splitlines()
        parsed = []
        for line in lines:
            try:
                parsed.append(json.loads(line))
            except ValueError:
                pass
        return parsed

    def wait_event(document_id, event, previous=0):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            matches = [
                e
                for e in events()
                if e.get("document_id") == document_id and e.get("event") == event
            ]
            if len(matches) > previous:
                return matches[-1]
            time.sleep(0.1)
        raise AssertionError(f"Missing {event} for {document_id}")

    def counts(document_id):
        sql = f"SELECT chunk_count, (SELECT count(*) FROM chunks WHERE document_id={document_id}), (SELECT count(DISTINCT chunk_index) FROM chunks WHERE document_id={document_id}) FROM documents WHERE id={document_id}"
        return run(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "insighthub",
            "-d",
            "insighthub",
            "-At",
            "-c",
            sql,
        ).strip()

    def container_state(service):
        container_id = run("ps", "-aq", service).strip()
        return json.loads(
            subprocess.check_output(["docker", "inspect", container_id], text=True)
        )[0]

    def wait_healthy(service):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            state = container_state(service)
            if state["State"].get("Health", {}).get("Status") == "healthy":
                return state
            time.sleep(0.2)
        raise AssertionError(f"{service} did not recover within 30s")

    try:
        sample = Path("sample-docs/so-tay-van-hanh.md").read_bytes()
        measurements = []
        for i in range(6):
            started = time.monotonic()
            code, doc = upload(sample, f"latency-day1-{time.time_ns()}.md")
            elapsed = time.monotonic() - started
            assert code == 202, doc
            ids.append(doc["id"])
            result = ready(doc["id"])
            to_ready = time.monotonic() - started
            measurements.append(
                {
                    "warmup": i == 0,
                    "document_id": doc["id"],
                    "status": code,
                    "upload_seconds": elapsed,
                    "ready_seconds": to_ready,
                    "chunks": result["chunk_count"],
                }
            )
            if i > 0:
                assert elapsed < 1 and to_ready < 30
        report["latency"] = {
            "file": "sample-docs/so-tay-van-hanh.md",
            "sha256": hashlib.sha256(sample).hexdigest(),
            "bytes": len(sample),
            "runs": measurements,
            "median_upload_seconds": statistics.median(
                r["upload_seconds"] for r in measurements[1:]
            ),
            "max_upload_seconds": max(r["upload_seconds"] for r in measurements[1:]),
        }

        # Keep the worker running when Redis disappears. No manual worker start
        # is allowed here: this assertion must prove automatic recovery.
        worker_before = wait_healthy("ingestion-worker")
        filename = f"redis-outage-{time.time_ns()}.txt"
        content = b"Redis outage recovery keeps the failed document identity."
        run("stop", "redis")
        code, rejected = upload(content, filename)
        assert code == 503 and rejected["code"] == "queue_unavailable"
        _, raw = request("/documents")
        failed = next(d for d in json.loads(raw) if d["filename"] == filename)
        ids.append(failed["id"])
        assert failed["status"] == "failed" and failed["chunk_count"] == 0
        deadline = time.monotonic() + 15
        while (
            container_state("ingestion-worker")["RestartCount"]
            <= worker_before["RestartCount"]
        ):
            assert time.monotonic() < deadline, (
                "Worker did not restart after Redis loss"
            )
            time.sleep(0.2)
        run("start", "redis")
        restored_at = time.monotonic()
        wait_healthy("redis")
        code, retried = upload(content, filename, f"/documents/{failed['id']}/retry")
        assert code == 202 and retried["id"] == failed["id"]
        result = ready(failed["id"])
        recovered_seconds = time.monotonic() - restored_at
        assert recovered_seconds < 30
        worker_after = wait_healthy("ingestion-worker")
        assert worker_after["RestartCount"] > worker_before["RestartCount"]
        assert counts(failed["id"]) == "1|1|1"
        report["redis_outage_recovery"] = {
            "worker_manually_started": False,
            "document_id": failed["id"],
            "status": result["status"],
            "chunks": result["chunk_count"],
            "restart_count_before": worker_before["RestartCount"],
            "restart_count_after": worker_after["RestartCount"],
            "ready_after_redis_start_seconds": recovered_seconds,
        }

        payload = (
            "Lifecycle test document: Redis worker preserves atomic chunks.\n" * 25000
        ).encode()
        code, doc = upload(payload, "lifecycle-day1.txt")
        assert code == 202, doc
        document_id = doc["id"]
        ids.append(document_id)
        started_event = wait_event(document_id, "ingestion_started")
        completed_before_signal = any(
            e.get("event") == "ingestion_completed"
            and e.get("document_id") == document_id
            for e in events()
        )
        assert not completed_before_signal, (
            "Work finished too early to establish in-flight SIGTERM"
        )
        stop_started = time.monotonic()
        run("stop", "ingestion-worker")
        stop_seconds = time.monotonic() - stop_started
        result = ready(document_id)
        before = counts(document_id)
        container_id = run("ps", "-aq", "ingestion-worker").strip()
        exit_code = subprocess.check_output(
            ["docker", "inspect", "--format", "{{.State.ExitCode}}", container_id],
            text=True,
        ).strip()
        assert exit_code == "0"
        run("start", "ingestion-worker")
        # Deliberate at-least-once redelivery, same identity/content, after success.
        run(
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            "import sys; from app.services.queue import enqueue_document; enqueue_document(int(sys.argv[1]), 'lifecycle-day1.txt', sys.stdin.buffer.read())",
            str(document_id),
            data=payload,
        )
        completion = wait_event(document_id, "ingestion_completed", previous=1)
        after = counts(document_id)
        assert before == after and len(set(before.split("|"))) == 1
        report["lifecycle"] = {
            "document_id": document_id,
            "payload_bytes": len(payload),
            "started_event": started_event,
            "completed_before_signal": completed_before_signal,
            "stop_seconds": stop_seconds,
            "exit_code": int(exit_code),
            "chunks": result["chunk_count"],
            "counts_before": before,
            "counts_after_redelivery": after,
            "redelivery_event": completion,
        }

        run("stop", "ingestion-worker")
        code, pending = upload(
            b"AOF preserves queued ingestion across Redis restart.",
            "persistence-day1.txt",
        )
        assert code == 202
        ids.append(pending["id"])
        run("restart", "redis")
        run("start", "ingestion-worker")
        result = ready(pending["id"])
        report["redis_restart"] = {
            "document_id": pending["id"],
            "status": result["status"],
            "chunks": result["chunk_count"],
        }
        health_code = "import urllib.request; print(urllib.request.urlopen('http://localhost:8081/readyz').status); print(urllib.request.urlopen('http://localhost:8081/metrics').read().decode())"
        health = run("exec", "-T", "ingestion-worker", "python", "-c", health_code)
        assert health.startswith("200") and "insighthub_worker_jobs_total" in health
        report["worker_health_metrics"] = "PASS"
        report["status"] = "PASS"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        run("start", "redis", "ingestion-worker")
        for document_id in ids:
            request(f"/documents/{document_id}", "DELETE")


if __name__ == "__main__":
    main()
