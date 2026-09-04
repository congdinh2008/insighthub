import asyncio
import logging

from app.core.metrics import ingestion_errors_total
from app.services.ingestion import process_document, _update_status

logger = logging.getLogger("insighthub.ingestion-worker")


async def ingest_document(ctx, document_id: int, filename: str, content: bytes) -> int:
    """Process one queued document while keeping the event loop responsive."""
    try:
        return await asyncio.to_thread(process_document, document_id, filename, content)
    except Exception:  # noqa: BLE001
        ingestion_errors_total.inc()
        _update_status(document_id, "failed")
        logger.exception("Ingestion failed for document %s", document_id)
        raise