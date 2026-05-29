import asyncio
import base64
import functools
import logging

from app.core.metrics import ingestion_queue_depth
from app.services.ingestion import _update_status, process_document

logger = logging.getLogger("insighthub.worker")


async def ingest_document(ctx, document_id: int, filename: str, content_b64: str):
    """ARQ task: chạy process_document() qua executor để không block event loop."""
    loop = asyncio.get_running_loop()
    content = base64.b64decode(content_b64)
    try:
        chunk_count = await loop.run_in_executor(
            None,
            functools.partial(process_document, document_id, filename, content),
        )
        logger.info("Document %s: %d chunks ingested", document_id, chunk_count)
    except Exception as exc:
        logger.error("Document %s ingestion failed: %s", document_id, exc)
        await loop.run_in_executor(
            None,
            functools.partial(_update_status, document_id, "failed"),
        )
        raise
    finally:
        ingestion_queue_depth.dec()
