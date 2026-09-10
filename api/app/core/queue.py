"""Enqueue only. api never processes ingestion jobs; ingestion-worker owns that."""

import logging

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import Settings
from app.core.errors import QueueUnavailable

logger = logging.getLogger("insighthub.queue")


async def create_queue_pool(settings: Settings) -> ArqRedis | None:
    try:
        return await create_pool(RedisSettings.from_dsn(settings.redis_url))
    except Exception:
        logger.warning("Redis queue unavailable at startup")
        return None


async def close_queue_pool(pool: ArqRedis | None) -> None:
    if pool is not None:
        await pool.close()


async def enqueue_ingestion(
    pool: ArqRedis | None, document_id: int, filename: str, content: bytes
) -> None:
    if pool is None:
        raise QueueUnavailable()
    try:
        job = await pool.enqueue_job("ingest_document", document_id, filename, content)
    except Exception:
        raise QueueUnavailable() from None
    if job is None:
        raise QueueUnavailable()
