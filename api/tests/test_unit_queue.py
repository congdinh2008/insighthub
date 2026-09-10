import asyncio
import json
import threading
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from support import configured

from app.services.queue import enqueue_document, redis_settings
from app.worker import ingest_document, run_document


class QueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_enqueue_uses_stable_id_and_configured_queue(self):
        pool = MagicMock(
            enqueue_job=AsyncMock(return_value=object()), aclose=AsyncMock()
        )
        with (
            configured(ingestion_queue="test:queue"),
            patch("app.services.queue.create_pool", AsyncMock(return_value=pool)),
        ):
            await enqueue_document(42)
        pool.enqueue_job.assert_awaited_once_with(
            "ingest_document", 42, _job_id="document:42", _queue_name="test:queue"
        )
        pool.aclose.assert_awaited_once()

    async def test_duplicate_job_is_not_a_new_acknowledgement(self):
        pool = MagicMock(enqueue_job=AsyncMock(return_value=None), aclose=AsyncMock())
        with patch("app.services.queue.create_pool", AsyncMock(return_value=pool)):
            with self.assertRaises(RuntimeError):
                await enqueue_document(42)
        pool.aclose.assert_awaited_once()

    async def test_enqueue_timeout_is_bounded_and_closes_connection(self):
        async def never_acknowledges(*args, **kwargs):
            await asyncio.Event().wait()

        pool = MagicMock(
            enqueue_job=AsyncMock(side_effect=never_acknowledges), aclose=AsyncMock()
        )
        with (
            configured(enqueue_timeout_seconds=0.05),
            patch("app.services.queue.create_pool", AsyncMock(return_value=pool)),
        ):
            with self.assertRaises(TimeoutError):
                await asyncio.wait_for(enqueue_document(42), timeout=0.5)
        pool.aclose.assert_awaited_once()

    async def test_close_failure_does_not_erase_acknowledged_enqueue(self):
        pool = MagicMock(
            enqueue_job=AsyncMock(return_value=object()),
            aclose=AsyncMock(side_effect=OSError()),
        )
        with patch("app.services.queue.create_pool", AsyncMock(return_value=pool)):
            await enqueue_document(42)

    async def test_worker_event_loop_stays_responsive_and_cancellation_waits_for_thread(
        self,
    ):
        started, release = threading.Event(), threading.Event()

        def blocked(document_id):
            started.set()
            release.wait(timeout=3)
            return "ready"

        with patch("app.worker.run_document", side_effect=blocked):
            task = asyncio.create_task(ingest_document({}, 42))
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 1))
                task.cancel()
                await asyncio.sleep(0.01)
                self.assertFalse(task.done())
            finally:
                release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task


class WorkerTests(unittest.TestCase):
    def test_redis_connection_has_no_hidden_admission_retries(self):
        with configured(redis_url="redis://redis:6379/2", enqueue_timeout_seconds=0.2):
            settings = redis_settings()
        self.assertEqual(settings.database, 2)
        self.assertEqual(settings.conn_retries, 0)
        self.assertEqual(settings.conn_timeout, 1)

    def test_completed_event_is_correlated_and_emitted_after_processing(self):
        with (
            patch("app.worker.get_conn") as conn,
            patch("app.worker.payload_path") as path,
            patch("app.worker.process_document") as process,
            self.assertLogs("insighthub.worker", level="INFO") as logs,
        ):
            conn.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = (
                "test.txt",
            )
            path.return_value.open.return_value.__enter__.return_value.read.return_value = b"content"

            def completed(*args):
                self.assertEqual(logs.records, [])

            process.side_effect = completed
            self.assertEqual(run_document(42), "ready")
        process.assert_called_once_with(42, "test.txt", b"content")
        event = json.loads(logs.records[0].getMessage())
        self.assertEqual(event["event"], "ingestion_completed")
        self.assertEqual(event["document_id"], 42)
        self.assertEqual(event["status"], "ready")
        self.assertIsNotNone(datetime.fromisoformat(event["timestamp"]).tzinfo)

    def test_worker_does_not_log_provider_body_or_false_completion(self):
        with (
            patch("app.worker.get_conn", side_effect=RuntimeError("secret document")),
            patch("app.worker.mark_pending_failed") as marker,
            self.assertLogs("insighthub.worker", level="INFO") as logs,
        ):
            self.assertEqual(run_document(42), "failed")
        marker.assert_called_once_with(42, "payload_or_worker_error")
        self.assertNotIn("secret", " ".join(logs.output))
        self.assertNotIn("ingestion_completed", " ".join(logs.output))
