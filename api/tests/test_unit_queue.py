# isort: skip_file
import asyncio
import time
import unittest
from unittest.mock import AsyncMock, patch

from support import configured
from fastapi.testclient import TestClient
from app.main import app
from app.core.errors import QueueUnavailable
from app.core.queue import enqueue_document


class QueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_enqueue_carries_exact_payload_and_stable_id(self):
        pool = AsyncMock()
        with (
            configured(ingestion_queue="test:queue"),
            patch("app.core.queue.create_pool", return_value=pool),
        ):
            await enqueue_document(7, "file.txt", b"payload")
        pool.enqueue_job.assert_awaited_once_with(
            "process_document",
            7,
            "file.txt",
            b"payload",
            _job_id="test:queue:document:7",
            _queue_name="test:queue",
            _expires=604800,
        )
        pool.aclose.assert_awaited_once()

    async def test_failure_and_duplicate_are_not_acknowledged(self):
        for result in (None, RuntimeError("SECRET")):
            pool = AsyncMock()
            if isinstance(result, Exception):
                pool.enqueue_job.side_effect = result
            else:
                pool.enqueue_job.return_value = result
            with (
                patch("app.core.queue.create_pool", return_value=pool),
                self.assertRaises(QueueUnavailable) as error,
            ):
                await enqueue_document(7, "file.txt", b"payload")
            self.assertNotIn("SECRET", str(error.exception))
            pool.aclose.assert_awaited_once()

    async def test_queue_timeout_is_bounded(self):
        async def slow(*args, **kwargs):
            await asyncio.sleep(10)

        with patch("app.core.queue.create_pool", side_effect=slow):
            start = time.monotonic()
            with self.assertRaises(QueueUnavailable):
                await enqueue_document(7, "file.txt", b"payload")
            self.assertLess(time.monotonic() - start, 1.5)


class UploadAcceptanceTests(unittest.TestCase):
    def test_enqueue_failure_remains_503_when_status_update_fails(self):
        with (
            patch("app.routers.documents.create_pending_document", return_value=7),
            patch(
                "app.routers.documents.enqueue_document", side_effect=QueueUnavailable()
            ),
            patch(
                "app.routers.documents.mark_enqueue_failed",
                side_effect=RuntimeError("SECRET"),
            ),
            self.assertLogs("app.routers.documents", level="WARNING") as logs,
        ):
            response = TestClient(app).post(
                "/documents", files={"file": ("file.txt", b"payload")}
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "queue_unavailable")
        self.assertNotIn("SECRET", response.text)
        self.assertNotIn("SECRET", " ".join(logs.output))

    def test_returns_pending_only_after_enqueue_and_never_calls_pipeline(self):
        events = []

        def create(*args):
            events.append("committed")
            return 7

        async def enqueue(*args):
            self.assertEqual(events, ["committed"])
            events.append("enqueued")

        with (
            patch("app.routers.documents.create_pending_document", side_effect=create),
            patch("app.routers.documents.enqueue_document", side_effect=enqueue),
            patch("app.services.ingestion.process_document") as pipeline,
        ):
            response = TestClient(app).post(
                "/documents", files={"file": ("file.txt", b"payload")}
            )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            (
                response.json()["id"],
                response.json()["status"],
                response.json()["chunk_count"],
            ),
            (7, "pending", 0),
        )
        self.assertEqual(events, ["committed", "enqueued"])
        pipeline.assert_not_called()

    def test_enqueue_failure_is_503_and_compensated(self):
        with (
            patch("app.routers.documents.create_pending_document", return_value=7),
            patch(
                "app.routers.documents.enqueue_document", side_effect=QueueUnavailable()
            ),
            patch("app.routers.documents.mark_enqueue_failed") as mark,
        ):
            response = TestClient(app).post(
                "/documents", files={"file": ("file.txt", b"payload")}
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "queue_unavailable")
        mark.assert_called_once_with(7)
