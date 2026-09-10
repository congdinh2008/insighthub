"""ARQ job handlers. Calls process_document unchanged - no parallel ingestion logic here."""

import asyncio

from app.core.errors import ServiceError
from app.services.ingestion import process_document

from worker.logging_config import log_event


async def ingest_document(ctx, document_id: int, filename: str, content: bytes) -> None:
    try:
        chunk_count = await asyncio.to_thread(
            process_document, document_id, filename, content
        )
    except ServiceError as exc:
        # process_document already committed status='failed' durably; a deterministic
        # failure (invalid document, conflict, index mismatch) won't succeed on retry.
        log_event(
            "ingestion_failed",
            document_id=document_id,
            status="failed",
            code=exc.code,
        )
        return
    log_event(
        "ingestion_completed",
        document_id=document_id,
        status="ready",
        chunk_count=chunk_count,
    )
