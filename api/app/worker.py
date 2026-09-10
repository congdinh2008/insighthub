"""ARQ entry point sharing the API image, DB, pipeline and retained payloads."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.core.db import close_pool, get_conn, initialize_database
from app.core.errors import DocumentNotFound, InvalidDocument, ServiceError
from app.services.ingestion import process_document
from app.services.payloads import mark_pending_failed, payload_path
from app.services.queue import redis_settings

logger = logging.getLogger("insighthub.worker")


def run_document(document_id: int) -> str:
    try:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT filename FROM documents WHERE id = %s", (document_id,)
            ).fetchone()
        if row is None:
            raise DocumentNotFound()
        with payload_path(document_id).open("rb") as stream:
            content = stream.read(get_settings().max_upload_bytes + 1)
        if len(content) > get_settings().max_upload_bytes:
            raise InvalidDocument()
        process_document(document_id, row[0], content)
    except Exception as exc:  # noqa: BLE001 - sanitize errors before ARQ can log them
        code = exc.code if isinstance(exc, ServiceError) else "payload_or_worker_error"
        try:
            mark_pending_failed(document_id, code)
        except Exception:  # noqa: BLE001 - DB outage must have a sanitized event
            # Never log driver/provider bodies. DB outage may prevent persisting
            # failure; this event explicitly requires later reconciliation.
            code = "failure_status_unconfirmed"
        logger.warning(
            json.dumps(
                {
                    "event": "ingestion_failed",
                    "document_id": document_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error_code": code,
                }
            )
        )
        return "failed"
    logger.info(
        json.dumps(
            {
                "event": "ingestion_completed",
                "document_id": document_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "ready",
            }
        )
    )
    return "ready"


async def ingest_document(ctx: dict[str, Any], document_id: int) -> str:
    # The sync DB/provider work runs outside ARQ's event loop. If cancelled,
    # finish this thread before allowing ARQ to replay it; row locks and hashes
    # also protect replay after abrupt process termination.
    task = asyncio.create_task(asyncio.to_thread(run_document, document_id))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        await task
        raise


async def startup(ctx: dict[str, Any]) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for name in ("httpx", "httpcore", "pypdf", "psycopg.pool"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    await asyncio.to_thread(initialize_database)


async def shutdown(ctx: dict[str, Any]) -> None:
    await asyncio.to_thread(close_pool)


class WorkerSettings:
    functions = (ingest_document,)
    redis_settings = redis_settings()
    queue_name = get_settings().ingestion_queue
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 2
    max_tries = 3
    job_timeout = 300
    health_check_interval = 5
    # A completed result would reserve document:<id> and block a later manual retry.
    keep_result = 0
    log_results = False
