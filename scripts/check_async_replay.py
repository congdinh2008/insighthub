"""Run inside the API image against the freshly measured fixture document.

Enqueues two distinct ARQ jobs for the same ID to exercise DB idempotency even
when queue-level deduplication is bypassed. No document or payload is deleted.
"""

import asyncio
import hashlib
import json
import sys
import uuid

from arq import create_pool

from app.core.config import get_settings
from app.core.db import close_pool, get_conn
from app.services.payloads import payload_path
from app.services.queue import redis_settings


def snapshot(document_id: int):
    with get_conn() as conn:
        document = conn.execute(
            "SELECT filename, status, chunk_count, content_sha256, pipeline_id, "
            "embedding_identity_id, error_code FROM documents WHERE id = %s",
            (document_id,),
        ).fetchone()
        chunks = conn.execute(
            "SELECT id, chunk_index, chunk_text, embedding::text, embedding_identity_id "
            "FROM chunks WHERE document_id = %s ORDER BY chunk_index",
            (document_id,),
        ).fetchall()
    return document, chunks


async def main(document_id: int) -> None:
    settings = get_settings()
    assert settings.rag_mode == "fixture" and settings.embedding_provider == "fixture"
    before = snapshot(document_id)
    assert before[0] is not None and before[0][0].startswith("day1-async-")
    assert before[0][1] == "ready" and before[0][2] == len(before[1]) > 0
    payload_hash = hashlib.sha256(payload_path(document_id).read_bytes()).hexdigest()
    assert payload_hash == before[0][3]
    pool = await create_pool(redis_settings())
    try:
        jobs = [
            await pool.enqueue_job(
                "ingest_document",
                document_id,
                _job_id="replay-check:" + uuid.uuid4().hex,
                _queue_name=settings.ingestion_queue,
            )
            for _ in range(2)
        ]
        assert all(job is not None for job in jobs)
        await asyncio.sleep(1)
        after = snapshot(document_id)
        assert after == before, "Replay changed stored chunks or metadata"
        assert (
            hashlib.sha256(payload_path(document_id).read_bytes()).hexdigest()
            == payload_hash
        )
        print(
            json.dumps(
                {
                    "document_id": document_id,
                    "replays": 2,
                    "chunk_count": len(after[1]),
                    "chunks_and_metadata_unchanged": True,
                    "payload_retained": True,
                    "jobs_enqueued": len(jobs),
                }
            )
        )
    finally:
        await pool.aclose()
        close_pool()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1])))
