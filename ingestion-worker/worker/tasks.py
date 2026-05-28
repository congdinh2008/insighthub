"""
InsightHub — Ingestion Worker Tasks (ARQ)

Nhận job từ Redis queue, gọi process_document() trong thread pool
để không block event loop của ARQ.
"""
import asyncio
import logging

from app.core.metrics import ingestion_queue_depth
from app.services.ingestion import _update_status, process_document

logger = logging.getLogger("insighthub.worker")


async def ingest_document(
    ctx: dict,
    document_id: int,
    filename: str,
    content: bytes,
) -> int:
    """ARQ task: chunk + embed + store một tài liệu.

    process_document() dùng psycopg sync pool — chạy trong executor
    để tránh block event loop ARQ.
    """
    # Chỉ dec khi là lần thử đầu tiên — tránh drift gauge khi ARQ retry
    if ctx.get("job_try", 1) == 1:
        ingestion_queue_depth.dec()
    logger.info(
        "Worker nhận job document_id=%d filename=%s try=%d",
        document_id,
        filename,
        ctx.get("job_try", 1),
    )

    loop = asyncio.get_event_loop()
    try:
        chunk_count: int = await loop.run_in_executor(
            None, process_document, document_id, filename, content
        )
        logger.info(
            "Document %d xử lý xong: %d chunks", document_id, chunk_count
        )
        return chunk_count
    except Exception as exc:
        logger.error(
            "Document %d thất bại: %s", document_id, exc, exc_info=True
        )
        await loop.run_in_executor(None, _update_status, document_id, "failed")
        raise
