"""Opt in with RUN_DB_TESTS=1 and mount init.sql as TEST_SCHEMA_PATH in Docker.

Each test run owns a random PostgreSQL schema. Only that schema is truncated/dropped.
No paid providers are called. A missing DB/schema fixture fails an opted-in run.
"""

import concurrent.futures
import asyncio
import hashlib
import os
from pathlib import Path
import threading
import tempfile
import unittest
import uuid
from unittest.mock import patch

from support import configured, real_config
import psycopg
from psycopg import sql
from psycopg_pool import ConnectionPool
from fastapi.testclient import TestClient

from app.core import db
from app.core.config import get_settings
from app.core.errors import (
    DocumentConflict,
    IndexIdentityConflict,
    ProviderError,
    SchemaMismatch,
)
from app.core.index import check_schema
from app.main import app
from app.services.embeddings import _local_embed
from app.services.ingestion import process_document
from app.services.retrieval import retrieve
from app.services.payloads import payload_path, mark_pending_failed
from app.worker import ingest_document


@unittest.skipUnless(
    os.environ.get("RUN_DB_TESTS") == "1",
    "Set RUN_DB_TESTS=1 for isolated PostgreSQL integration tests",
)
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn = os.environ.get("TEST_DATABASE_URL") or get_settings().database_url
        cls.schema = "test_insighthub_" + uuid.uuid4().hex
        source = Path(
            os.environ.get(
                "TEST_SCHEMA_PATH",
                str(Path(__file__).resolve().parents[2] / "infra/db/init.sql"),
            )
        )
        cls.schema_sql = source.read_text()
        cls.old_pool = db._pool
        with psycopg.connect(cls.dsn, autocommit=True) as conn:
            # Extension must be installed by the DB bootstrap, never by the test run.
            if not conn.execute(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ).fetchone():
                raise RuntimeError(
                    "Initialize pgvector using infra/db/init.sql before integration tests"
                )
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(cls.schema)))
        cls.addClassCleanup(cls.cleanup_schema)
        with psycopg.connect(
            cls.dsn, options=f"-csearch_path={cls.schema},public"
        ) as conn:
            conn.execute(cls.schema_sql)
        db._pool = ConnectionPool(
            conninfo=cls.dsn,
            min_size=2,
            max_size=10,
            configure=db._configure,
            kwargs={"options": f"-csearch_path={cls.schema},public"},
            open=True,
        )
        db._pool.wait(timeout=15)

    @classmethod
    def cleanup_schema(cls):
        if db._pool is not cls.old_pool:
            db._pool.close()
        db._pool = cls.old_pool
        with psycopg.connect(cls.dsn, autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(cls.schema))
            )

    def setUp(self):
        self.payloads = tempfile.TemporaryDirectory()
        self.addCleanup(self.payloads.cleanup)
        self.config = configured(payload_dir=self.payloads.name)
        self.config.__enter__()
        self.addCleanup(self.config.__exit__, None, None, None)
        with db.get_conn() as conn:
            conn.execute(
                "TRUNCATE chunks, documents, embedding_index RESTART IDENTITY CASCADE"
            )
        self.client = TestClient(app)
        self.jobs = []

        async def enqueue(document_id):
            self.jobs.append(document_id)

        queue_patch = patch(
            "app.routers.documents.enqueue_document", side_effect=enqueue
        )
        queue_patch.start()
        self.addCleanup(queue_patch.stop)

    def finish_upload(self, response, expected="ready"):
        self.assertEqual(response.status_code, 202, response.text)
        document_id = response.json()["id"]
        self.assertEqual(response.json()["status"], "pending")
        self.assertEqual(self.state(document_id)[0], "pending")
        self.assertIn(document_id, self.jobs)
        self.assertEqual(asyncio.run(ingest_document({}, document_id)), expected)
        document = next(
            d for d in self.client.get("/documents").json() if d["id"] == document_id
        )
        self.assertEqual(document["status"], expected)
        return document

    def create_document(self, filename="test.txt"):
        with db.get_conn() as conn:
            return conn.execute(
                "INSERT INTO documents(filename) VALUES (%s) RETURNING id",
                (filename,),
            ).fetchone()[0]

    def state(self, document_id):
        with db.get_conn() as conn:
            return conn.execute(
                "SELECT status, chunk_count, content_sha256, error_code, "
                "(SELECT count(*) FROM chunks WHERE document_id = documents.id) "
                "FROM documents WHERE id = %s",
                (document_id,),
            ).fetchone()

    def test_fixture_upload_retrieve_chat_metrics_delete_end_to_end(self):
        self.assertEqual(self.client.get("/readyz").status_code, 200)
        self.assertEqual(
            self.client.post("/chat", json={"question": "RAG?"}).status_code, 404
        )
        response = self.client.post(
            "/documents", files={"file": ("rag.txt", b"RAG uses retrieved documents.")}
        )
        ready = self.finish_upload(response)
        document = response.json()
        self.assertEqual(document["mode"], "fixture")
        self.assertEqual(ready["chunk_count"], 1)
        self.assertEqual(self.client.get("/documents").json()[0]["status"], "ready")
        chat = self.client.post(
            "/chat", json={"question": "RAG uses retrieved documents."}
        )
        self.assertEqual(chat.status_code, 200, chat.text)
        self.assertIn("FIXTURE", chat.json()["answer"])
        self.assertEqual(chat.json()["sources"], ["rag.txt"])
        self.assertAlmostEqual(chat.json()["contexts"][0]["similarity"], 1, places=3)
        self.assertEqual(chat.json()["usage"]["source"], "unavailable")
        metrics = self.client.get("/metrics")
        self.assertEqual(metrics.status_code, 200)
        self.assertIn('insighthub_documents_total{status="ready"} 1.0', metrics.text)
        self.assertEqual(
            self.client.delete(f"/documents/{document['id']}").status_code, 204
        )
        with db.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT count(*) FROM chunks").fetchone()[0], 0
            )
        self.assertIn(
            'insighthub_documents_total{status="ready"} 0.0',
            self.client.get("/metrics").text,
        )

    def test_successful_retry_is_noop_and_conflicting_payload_is_409(self):
        document_id = self.create_document()
        first = process_document(document_id, "test.txt", b"hello world")
        with patch("app.services.ingestion.embed") as provider:
            self.assertEqual(
                process_document(document_id, "test.txt", b"hello world"), first
            )
            provider.assert_not_called()
        for filename, content in (
            ("test.txt", b"changed"),
            ("other.txt", b"hello world"),
        ):
            with self.assertRaises(DocumentConflict):
                process_document(document_id, filename, content)
        state = self.state(document_id)
        self.assertEqual((state[0], state[1], state[4]), ("ready", first, first))
        self.assertIsNotNone(state[2])

    def test_concurrent_successful_retries_call_provider_once(self):
        document_id = self.create_document()
        started, release = threading.Event(), threading.Event()

        def slow_embed(texts, input_type):
            started.set()
            self.assertTrue(release.wait(timeout=5))
            return _local_embed(texts, 1024)

        with patch("app.services.ingestion.embed", side_effect=slow_embed) as provider:
            with concurrent.futures.ThreadPoolExecutor(2) as executor:
                first = executor.submit(
                    process_document, document_id, "test.txt", b"same"
                )
                self.assertTrue(started.wait(timeout=3))
                second = executor.submit(
                    process_document, document_id, "test.txt", b"same"
                )
                release.set()
                self.assertEqual(first.result(timeout=5), second.result(timeout=5))
            self.assertEqual(provider.call_count, 1)
        self.assertEqual(self.state(document_id)[4], 1)

    def test_failed_attempt_and_concurrent_retry_end_ready(self):
        document_id = self.create_document()
        started, release = threading.Event(), threading.Event()
        calls = []

        def fail_once(texts, input_type):
            calls.append(True)
            if len(calls) == 1:
                started.set()
                release.wait(timeout=5)
                raise ProviderError()
            return _local_embed(texts, 1024)

        with patch("app.services.ingestion.embed", side_effect=fail_once):
            with concurrent.futures.ThreadPoolExecutor(2) as executor:
                first = executor.submit(
                    process_document, document_id, "test.txt", b"same"
                )
                self.assertTrue(started.wait(timeout=3))
                second = executor.submit(
                    process_document, document_id, "test.txt", b"same"
                )
                release.set()
                with self.assertRaises(ProviderError):
                    first.result(timeout=5)
                self.assertEqual(second.result(timeout=5), 1)
        self.assertEqual(self.state(document_id)[0], "ready")
        self.assertEqual(self.state(document_id)[4], 1)
        self.assertIsNone(self.state(document_id)[3])

    def test_failed_vectors_are_atomic_and_can_retry(self):
        document_id = self.create_document()
        for invalid in ([], [[float("nan")] * 1024], [[1.0] * 1023]):
            with (
                patch("app.services.ingestion.embed", return_value=invalid),
                self.assertRaises(ProviderError),
            ):
                process_document(document_id, "test.txt", b"content")
            state = self.state(document_id)
            self.assertEqual((state[0], state[1], state[4]), ("failed", 0, 0))
            self.assertEqual(state[3], "provider_error")
            with db.get_conn() as conn:
                self.assertEqual(
                    conn.execute("SELECT count(*) FROM embedding_index").fetchone()[0],
                    0,
                )
        self.assertEqual(process_document(document_id, "test.txt", b"content"), 1)

    def test_mid_insert_database_failure_rolls_back_all_chunks(self):
        document_id = self.create_document()
        with db.get_conn() as conn:
            conn.execute(
                "CREATE FUNCTION reject_second() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN IF NEW.chunk_index = 1 THEN RAISE EXCEPTION 'secret'; END IF; "
                "RETURN NEW; END $$"
            )
            conn.execute(
                "CREATE TRIGGER reject_second BEFORE INSERT ON chunks "
                "FOR EACH ROW EXECUTE FUNCTION reject_second()"
            )
        try:
            with configured(chunk_size=4, chunk_overlap=0):
                with self.assertRaises(Exception) as raised:
                    process_document(document_id, "test.txt", b"a b c d e f")
                self.assertNotIn("secret", str(raised.exception))
        finally:
            with db.get_conn() as conn:
                conn.execute("DROP TRIGGER reject_second ON chunks")
                conn.execute("DROP FUNCTION reject_second()")
        state = self.state(document_id)
        self.assertEqual((state[0], state[1], state[4]), ("failed", 0, 0))

    def test_empty_extracted_text_is_accepted_then_failed(self):
        response = self.client.post(
            "/documents", files={"file": ("empty.txt", b" \n ")}
        )
        document = self.finish_upload(response, "failed")
        self.assertEqual(document["status"], "failed")
        self.assertEqual(document["chunk_count"], 0)
        self.assertEqual(document["error_code"], "invalid_document")

    def test_index_identity_change_rejects_query_upload_and_readiness(self):
        self.finish_upload(
            self.client.post("/documents", files={"file": ("test.txt", b"content")})
        )
        with (
            configured(embedding_revision="2"),
            patch("app.services.retrieval.embed") as provider,
        ):
            with self.assertRaises(IndexIdentityConflict):
                retrieve("question")
            provider.assert_not_called()
            response = self.client.post(
                "/documents", files={"file": ("new.txt", b"new content")}
            )
            document = self.finish_upload(response, "failed")
            self.assertEqual(document["error_code"], "index_identity_conflict")
            self.assertEqual(self.client.get("/readyz").status_code, 503)
        with db.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT count(*) FROM chunks").fetchone()[0], 1
            )

    def test_same_dimension_real_provider_cannot_query_fixture_index(self):
        self.finish_upload(
            self.client.post("/documents", files={"file": ("test.txt", b"content")})
        )
        with real_config(), patch("app.services.retrieval.embed") as provider:
            with self.assertRaises(IndexIdentityConflict):
                retrieve("question")
        provider.assert_not_called()

    def test_dimension_mismatch_is_rejected_before_provider(self):
        with configured(embedding_dim=768), db.get_conn() as conn:
            with self.assertRaises(SchemaMismatch):
                check_schema(conn)

    def test_real_gateway_full_pipeline_with_mock_http(self):
        def embedding_response(*args, **kwargs):
            return {
                "data": [
                    {"index": i, "embedding": [1.0] * 1024}
                    for i in range(len(kwargs["payload"]["input"]))
                ],
                "usage": {"prompt_tokens": 5},
            }

        with (
            real_config(),
            patch(
                "app.services.embeddings.post_json",
                side_effect=embedding_response,
            ),
            patch(
                "app.services.llm.post_json",
                return_value={
                    "choices": [
                        {"message": {"content": "Supported answer [nguồn: real.txt]"}}
                    ],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 8},
                },
            ),
        ):
            upload = self.client.post(
                "/documents", files={"file": ("real.txt", b"content")}
            )
            self.finish_upload(upload)
            chat = self.client.post("/chat", json={"question": "question"})
            self.assertEqual(chat.status_code, 200, chat.text)
            self.assertEqual(chat.json()["mode"], "real")
            self.assertEqual(chat.json()["usage"]["input_tokens"], 12)
            self.assertEqual(chat.json()["usage"]["source"], "provider")

    def test_provider_failure_is_async_and_metadata_truthful(self):
        with (
            real_config(),
            patch("app.services.embeddings.post_json", side_effect=ProviderError()),
        ):
            response = self.client.post(
                "/documents", files={"file": ("real.txt", b"content")}
            )
            document = self.finish_upload(response, "failed")
        self.assertEqual(
            (document["status"], document["chunk_count"], document["error_code"]),
            ("failed", 0, "provider_error"),
        )

    def test_enqueue_failure_retains_payload_and_sets_failed(self):
        with patch(
            "app.routers.documents.enqueue_document",
            side_effect=ConnectionError("secret"),
        ):
            response = self.client.post(
                "/documents", files={"file": ("test.txt", b"retained")}
            )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", response.text)
        document_id = response.json()["detail"]["document_id"]
        self.assertEqual(self.state(document_id)[0], "failed")
        self.assertEqual(self.state(document_id)[3], "enqueue_unconfirmed")
        self.assertEqual(payload_path(document_id).read_bytes(), b"retained")
        # A late job after a lost acknowledgement can still complete safely.
        self.assertEqual(asyncio.run(ingest_document({}, document_id)), "ready")
        with patch("app.services.ingestion.embed") as provider:
            self.assertEqual(asyncio.run(ingest_document({}, document_id)), "ready")
        provider.assert_not_called()
        self.assertEqual(self.state(document_id)[4], 1)

    def test_lost_enqueue_reply_does_not_overwrite_worker_ready(self):
        async def accepted_then_timeout(document_id):
            await ingest_document({}, document_id)
            raise TimeoutError("secret")

        with patch(
            "app.routers.documents.enqueue_document", side_effect=accepted_then_timeout
        ):
            response = self.client.post(
                "/documents", files={"file": ("test.txt", b"retained")}
            )
        self.assertEqual(response.status_code, 503)
        document_id = response.json()["detail"]["document_id"]
        self.assertEqual(self.state(document_id)[0], "ready")
        self.assertIsNone(self.state(document_id)[3])
        self.assertEqual(self.state(document_id)[4], 1)
        self.assertTrue(payload_path(document_id).exists())

    def test_failure_marker_does_not_block_or_overwrite_locked_worker(self):
        document_id = self.create_document()
        started, release = threading.Event(), threading.Event()

        def slow_embed(texts, input_type):
            started.set()
            self.assertTrue(release.wait(timeout=5))
            return _local_embed(texts, 1024)

        with patch("app.services.ingestion.embed", side_effect=slow_embed):
            with concurrent.futures.ThreadPoolExecutor(2) as executor:
                worker = executor.submit(
                    process_document, document_id, "test.txt", b"same"
                )
                self.assertTrue(started.wait(timeout=3))
                try:
                    marker = executor.submit(
                        mark_pending_failed, document_id, "enqueue_unconfirmed"
                    )
                    marker.result(timeout=1)
                finally:
                    release.set()
                self.assertEqual(worker.result(timeout=5), 1)
        self.assertEqual(self.state(document_id)[0], "ready")
        self.assertIsNone(self.state(document_id)[3])

    def test_payload_storage_failure_rolls_back_admission_and_never_enqueues(self):
        with patch("app.services.payloads.os.fsync", side_effect=OSError("secret")):
            response = self.client.post(
                "/documents", files={"file": ("test.txt", b"content")}
            )
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("secret", response.text)
        self.assertEqual(self.jobs, [])
        self.assertEqual(self.client.get("/documents").json(), [])

    def test_worker_rejects_changed_payload_and_keeps_hash(self):
        response = self.client.post(
            "/documents", files={"file": ("test.txt", b"original")}
        )
        document_id = response.json()["id"]
        payload_path(document_id).write_bytes(b"changed")
        with patch("app.services.ingestion.embed") as provider:
            self.finish_upload(response, "failed")
        provider.assert_not_called()
        self.assertEqual(
            self.state(document_id)[2], hashlib.sha256(b"original").hexdigest()
        )
        self.assertEqual(self.state(document_id)[3], "document_conflict")
        self.assertEqual(self.state(document_id)[4], 0)

    def test_worker_missing_payload_is_failed_and_logs_no_completed_event(self):
        document_id = self.create_document()
        with self.assertLogs("insighthub.worker", level="INFO") as captured:
            self.assertEqual(asyncio.run(ingest_document({}, document_id)), "failed")
        self.assertEqual(self.state(document_id)[0], "failed")
        self.assertNotIn("ingestion_completed", " ".join(captured.output))

    def fail_uploaded_document(self, content=b"retry content"):
        with patch("app.services.ingestion.embed", side_effect=ProviderError()):
            response = self.client.post(
                "/documents", files={"file": ("retry.txt", content)}
            )
            document = self.finish_upload(response, "failed")
        return document["id"]

    def test_retry_failed_document_returns_202_then_ready_without_duplicate_chunks(self):
        document_id = self.fail_uploaded_document()
        response = self.client.post(f"/documents/{document_id}/retry")
        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(response.json()["status"], "pending")
        self.assertEqual(self.state(document_id)[0], "pending")
        self.assertEqual(asyncio.run(ingest_document({}, document_id)), "ready")
        with patch("app.services.ingestion.embed") as provider:
            self.assertEqual(asyncio.run(ingest_document({}, document_id)), "ready")
        provider.assert_not_called()
        self.assertEqual(self.state(document_id)[4], 1)

    def test_retry_rejects_pending_ready_and_missing_documents(self):
        pending = self.create_document()
        self.assertEqual(self.client.post(f"/documents/{pending}/retry").status_code, 409)
        ready = self.finish_upload(
            self.client.post("/documents", files={"file": ("ready.txt", b"ready")})
        )["id"]
        self.assertEqual(self.client.post(f"/documents/{ready}/retry").status_code, 409)
        missing = self.client.post("/documents/99999/retry")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["code"], "document_not_found")

    def test_retry_rejects_missing_or_changed_payload_without_enqueueing(self):
        document_id = self.fail_uploaded_document()
        payload_path(document_id).unlink()
        missing = self.client.post(f"/documents/{document_id}/retry")
        self.assertEqual(missing.status_code, 409)
        self.assertEqual(missing.json()["code"], "payload_unavailable")
        self.assertEqual(self.state(document_id)[0], "failed")
        self.assertNotIn(document_id, self.jobs[1:])

        other_id = self.fail_uploaded_document(b"original")
        payload_path(other_id).write_bytes(b"changed")
        changed = self.client.post(f"/documents/{other_id}/retry")
        self.assertEqual(changed.status_code, 409)
        self.assertEqual(changed.json()["code"], "document_conflict")
        self.assertEqual(self.state(other_id)[0], "failed")

    def test_retry_rejects_pipeline_mismatch_without_enqueueing(self):
        document_id = self.fail_uploaded_document()
        with configured(embedding_revision="different"):
            mismatch = self.client.post(f"/documents/{document_id}/retry")
        self.assertEqual(mismatch.status_code, 409)
        self.assertEqual(mismatch.json()["code"], "document_conflict")
        self.assertEqual(self.state(document_id)[0], "failed")

    def test_retry_enqueue_failure_keeps_payload_and_returns_document_id(self):
        document_id = self.fail_uploaded_document()
        with patch(
            "app.routers.documents.enqueue_document", side_effect=TimeoutError("secret")
        ):
            response = self.client.post(f"/documents/{document_id}/retry")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["document_id"], document_id)
        self.assertNotIn("secret", response.text)
        self.assertEqual(self.state(document_id)[0], "failed")
        self.assertEqual(self.state(document_id)[3], "enqueue_unconfirmed")
        self.assertTrue(payload_path(document_id).exists())
