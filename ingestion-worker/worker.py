"""ARQ entrypoint for atomic chunk/embed/pgvector ingestion."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.core.db import close_pool, get_conn, initialize_database
from app.core.errors import DocumentConflict, DocumentNotFound, ServiceError
from app.core.queue import redis_settings
from app.services.ingestion import process_document as ingest_atomic
from arq import Retry

logger = logging.getLogger("insighthub.worker")
MAX_ATTEMPTS = 4  # Initial attempt plus three retries, deferred by 1, 2, 4 seconds.


def configure_logging() -> None:
    # ARQ's default INFO messages include job arguments (private uploaded bytes).
    for name in (
        "arq.worker",
        "arq.connections",
        "httpx",
        "httpcore",
        "pypdf",
        "psycopg.pool",
    ):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.propagate = False


configure_logging()


def emit(event: str, document_id: int, **fields: Any) -> None:
    logger.info(
        json.dumps(
            {
                "event": event,
                "document_id": document_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **fields,
            }
        )
    )


def mark_failed(document_id: int, error_code: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET status = 'failed', error_code = %s "
            "WHERE id = %s AND status = 'pending'",
            (error_code, document_id),
        )


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    await asyncio.to_thread(initialize_database)


async def shutdown(ctx: dict[str, Any]) -> None:
    await asyncio.to_thread(close_pool)


async def process_document(
    ctx: dict[str, Any], document_id: int, filename: str, content: bytes
) -> int:
    """Run extract/chunk/embed/store off the event loop, preserving row locks."""
    attempt = ctx.get("job_try", 1)
    try:
        count = await asyncio.to_thread(
            ingest_atomic,
            document_id,
            filename,
            content,
            retry_pending=attempt < MAX_ATTEMPTS,
        )
    except (DocumentConflict, DocumentNotFound) as exc:
        # A stale/conflicting job must not change the legitimate document's state.
        emit("ingestion_rejected", document_id, error_code=exc.code, attempt=attempt)
        raise
    except Exception as exc:  # noqa: BLE001 - persist status and sanitize errors
        error = exc if isinstance(exc, ServiceError) else ServiceError()
        if error.status_code >= 500 and attempt < MAX_ATTEMPTS:
            delay = 2 ** (attempt - 1)
            emit(
                "ingestion_retry",
                document_id,
                error_code=error.code,
                attempt=attempt,
                retry_in_seconds=delay,
            )
            raise Retry(defer=delay) from None
        try:
            await asyncio.to_thread(mark_failed, document_id, error.code)
        except Exception:  # noqa: BLE001 - sanitize errors at the service boundary
            # A DB outage can prevent status persistence; never expose driver errors.
            emit("ingestion_status_unavailable", document_id, error_code=error.code)
        emit(
            "ingestion_failed",
            document_id,
            status="failed",
            error_code=error.code,
            attempt=attempt,
        )
        raise error from None
    emit(
        "ingestion_completed",
        document_id,
        status="ready",
        chunk_count=count,
        attempt=attempt,
    )
    return count


class WorkerSettings:
    functions = (process_document,)
    queue_name = get_settings().ingestion_queue
    redis_settings = redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 4
    job_timeout = 300
    job_completion_wait = 300
    max_tries = MAX_ATTEMPTS
    health_check_interval = 10
    keep_result = 0
    log_results = False
