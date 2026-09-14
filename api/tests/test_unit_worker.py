# isort: skip_file
import asyncio
import json
import threading
import unittest
from unittest.mock import patch

import support  # noqa: F401 - set fixture environment before importing the worker
from arq import Retry
from app.core.errors import (
    DocumentConflict,
    InvalidDocument,
    ProviderError,
    ServiceError,
)
import worker


class WorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_three_exponential_retries_then_terminal_error(self):
        with (
            patch("worker.ingest_atomic", side_effect=ProviderError()) as ingest,
            patch("worker.mark_failed") as mark,
            patch("worker.emit") as emit,
        ):
            for attempt, delay_ms in ((1, 1000), (2, 2000), (3, 4000)):
                with self.assertRaises(Retry) as error:
                    await worker.process_document(
                        {"job_try": attempt}, 42, "private.txt", b"private"
                    )
                self.assertEqual(error.exception.defer_score, delay_ms)
                self.assertTrue(ingest.call_args.kwargs["retry_pending"])
                mark.assert_not_called()
            with self.assertRaises(ProviderError):
                await worker.process_document(
                    {"job_try": 4}, 42, "private.txt", b"private"
                )
            self.assertEqual(ingest.call_count, 4)
            self.assertFalse(ingest.call_args.kwargs["retry_pending"])
            mark.assert_called_once_with(42, "provider_error")
            self.assertEqual(emit.call_args.args[0], "ingestion_failed")

    async def test_invalid_document_does_not_retry(self):
        with (
            patch("worker.ingest_atomic", side_effect=InvalidDocument()),
            patch("worker.mark_failed") as mark,
            self.assertRaises(InvalidDocument),
        ):
            await worker.process_document({"job_try": 1}, 42, "x.txt", b" ")
        mark.assert_called_once_with(42, "invalid_document")

    async def test_conflicting_job_does_not_mutate_existing_document(self):
        with (
            patch("worker.ingest_atomic", side_effect=DocumentConflict()),
            patch("worker.mark_failed") as mark,
            self.assertRaises(DocumentConflict),
        ):
            await worker.process_document({"job_try": 1}, 42, "x.txt", b"different")
        mark.assert_not_called()

    async def test_raw_error_is_sanitized(self):
        with (
            patch("worker.ingest_atomic", side_effect=RuntimeError("SECRET_DOCUMENT")),
            patch("worker.mark_failed"),
            self.assertLogs("insighthub.worker", level="INFO") as logs,
            self.assertRaises(ServiceError) as error,
        ):
            await worker.process_document(
                {"job_try": 4}, 42, "SECRET_FILE", b"SECRET_DOCUMENT"
            )
        self.assertNotIn("SECRET", str(error.exception))
        self.assertNotIn("SECRET", " ".join(logs.output))

    async def test_success_emits_correlated_safe_json(self):
        with (
            patch("worker.ingest_atomic", return_value=3),
            self.assertLogs("insighthub.worker", level="INFO") as logs,
        ):
            self.assertEqual(
                await worker.process_document(
                    {"job_try": 2}, 42, "private", b"private"
                ),
                3,
            )
        event = json.loads(logs.records[0].getMessage())
        self.assertEqual(
            (
                event["event"],
                event["document_id"],
                event["status"],
                event["chunk_count"],
            ),
            ("ingestion_completed", 42, "ready", 3),
        )
        self.assertIn("timestamp", event)
        self.assertNotIn("private", logs.records[0].getMessage())

    async def test_blocking_pipeline_does_not_block_event_loop(self):
        started, release = threading.Event(), threading.Event()

        def blocked(*args, **kwargs):
            started.set()
            release.wait(3)
            return 1

        with patch("worker.ingest_atomic", side_effect=blocked):
            task = asyncio.create_task(worker.process_document({}, 42, "x.txt", b"x"))
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 1))
                await asyncio.wait_for(asyncio.sleep(0), timeout=0.2)
            finally:
                release.set()
                await task
