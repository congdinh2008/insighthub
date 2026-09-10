"""Bounded ARQ admission; a lost reply is never treated as success."""

import asyncio
import math
from contextlib import suppress

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings


def redis_settings() -> RedisSettings:
    settings = RedisSettings.from_dsn(get_settings().redis_url)
    settings.conn_retries = 0
    # ARQ types this setting as whole seconds; the outer asyncio timeout still
    # enforces the precise, subsecond admission budget.
    settings.conn_timeout = math.ceil(get_settings().enqueue_timeout_seconds)
    return settings


async def enqueue_document(document_id: int) -> None:
    settings = get_settings()
    pool = None
    try:
        async with asyncio.timeout(settings.enqueue_timeout_seconds):
            pool = await create_pool(redis_settings())
            job = await pool.enqueue_job(
                "ingest_document",
                document_id,
                _job_id=f"document:{document_id}",
                _queue_name=settings.ingestion_queue,
            )
            if job is None:
                raise RuntimeError("Job admission not confirmed")
    finally:
        if pool is not None:
            # Closing a connection after an acknowledged enqueue must not turn
            # that acknowledgement into a false failure.
            with suppress(Exception):
                await asyncio.wait_for(pool.aclose(), timeout=0.1)
