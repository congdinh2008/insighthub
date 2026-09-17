import asyncio
import io
import json
import logging
import threading
from unittest.mock import AsyncMock, patch

import pytest
from app.core.errors import ProviderError, QueueUnavailable
from app.services.queue import enqueue
from arq import Retry
from arq.jobs import JobStatus
from redis.exceptions import ConnectionError
from worker import SafeJSONFormatter, ingest, main


@pytest.mark.parametrize("during_startup", [True, False])
def test_redis_disconnect_exits_for_restart_without_leaking_secrets(
    capsys, during_startup
):
    root = logging.getLogger()
    previous_handlers, previous_level = root.handlers, root.level
    try:
        with patch("worker.Worker") as worker:
            target = worker if during_startup else worker.return_value.run
            target.side_effect = ConnectionError("redis://private:secret@host/0")
            assert main() == 1
        output = capsys.readouterr().err
        event = json.loads(output)
        assert event["event"] == "worker_connection_lost"
        assert event["error_code"] == "queue_unavailable"
        assert "secret" not in output and "Traceback" not in output
    finally:
        root.handlers, root.level = previous_handlers, previous_level


def test_transient_retries_have_exponential_backoff():
    for attempt, delay in ((1, 1000), (2, 2000), (3, 4000)):
        with patch(
            "worker.process_document", side_effect=ProviderError(retryable=True)
        ):
            with pytest.raises(Retry) as error:
                asyncio.run(
                    ingest({"job_try": attempt, "job_id": "j"}, 1, "a.txt", b"text")
                )
            assert error.value.defer_score == delay
    with patch("worker.process_document", side_effect=ProviderError(retryable=True)):
        assert (
            asyncio.run(ingest({"job_try": 4, "job_id": "j"}, 1, "a.txt", b"text")) == 0
        )


def test_invalid_vectors_do_not_retry():
    with patch("worker.process_document", side_effect=ProviderError()) as process:
        assert (
            asyncio.run(ingest({"job_try": 1, "job_id": "j"}, 1, "a.txt", b"text")) == 0
        )
        process.assert_called_once()


def test_cancellation_drains_sync_thread_before_return():
    async def scenario():
        started, release, finished = (
            threading.Event(),
            threading.Event(),
            threading.Event(),
        )

        def processing(*args, **kwargs):
            started.set()
            assert release.wait(3)
            finished.set()
            return 1

        with patch("worker.process_document", side_effect=processing):
            task = asyncio.create_task(
                ingest({"job_try": 1, "job_id": "j"}, 1, "a.txt", b"text")
            )
            assert await asyncio.to_thread(started.wait, 1)
            task.cancel()
            await asyncio.sleep(0.03)
            assert not task.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert finished.is_set()

    asyncio.run(scenario())


def test_formatter_does_not_leak_payload_exception_or_arguments():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(SafeJSONFormatter())
    log = logging.getLogger("test-redaction")
    log.handlers = [handler]
    log.setLevel(logging.INFO)
    try:
        raise ValueError("provider-secret")
    except ValueError:
        log.exception(
            "job payload=%s",
            b"private-document",
            extra={
                "event": "ingestion_failed",
                "document_id": 9,
                "error_code": "provider_error",
            },
        )
    output = stream.getvalue()
    assert (
        "provider-secret" not in output
        and "private-document" not in output
        and "Traceback" not in output
    )
    assert json.loads(output)["document_id"] == 9


def test_ambiguous_enqueue_checks_same_job_identity():
    pool = AsyncMock()
    pool.enqueue_job.side_effect = ConnectionError("connection lost")
    with (
        patch("app.services.queue.create_pool", return_value=pool),
        patch("app.services.queue.Job.status", return_value=JobStatus.in_progress),
    ):
        assert asyncio.run(enqueue(7, "file.txt", b"text"))
    pool.aclose.assert_awaited_once()


def test_unavailable_queue_never_returns_success():
    pool = AsyncMock()
    pool.enqueue_job.side_effect = ConnectionError("secret")
    with (
        patch("app.services.queue.create_pool", return_value=pool),
        patch("app.services.queue.Job.status", side_effect=ConnectionError("secret")),
    ):
        with pytest.raises(QueueUnavailable) as error:
            asyncio.run(enqueue(7, "file.txt", b"text"))
        assert "secret" not in str(error.value)


def test_manual_retry_rejects_finishing_job_instead_of_stranding_pending():
    from app.core.errors import DocumentConflict

    pool = AsyncMock()
    pool.enqueue_job.return_value = None
    with patch("app.services.queue.create_pool", return_value=pool):
        with pytest.raises(DocumentConflict):
            asyncio.run(enqueue(7, "file.txt", b"text", require_new=True))


def test_ambiguous_manual_retry_cannot_accept_an_old_finishing_job():
    pool = AsyncMock()
    pool.enqueue_job.side_effect = ConnectionError("lost response")
    with (
        patch("app.services.queue.create_pool", return_value=pool),
        patch(
            "app.services.queue.Job.status", return_value=JobStatus.in_progress
        ) as status,
    ):
        with pytest.raises(QueueUnavailable):
            asyncio.run(enqueue(7, "file.txt", b"text", require_new=True))
        status.assert_not_called()
    pool.aclose.assert_awaited_once()
