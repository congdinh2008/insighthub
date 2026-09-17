"""Bounded ARQ enqueue; HTTP acceptance requires Redis acknowledgement."""

import asyncio
import logging

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.errors import QueueUnavailable

# ARQ connection diagnostics can contain operator credentials.
logging.getLogger("arq.connections").setLevel(logging.CRITICAL)


def redis_settings() -> RedisSettings:
    settings = RedisSettings.from_dsn(get_settings().redis_url)
    settings.conn_timeout = 0.5
    settings.conn_retries = 0
    return settings


async def enqueue_document(document_id: int, filename: str, content: bytes) -> None:
    pool = None
    try:
        async with asyncio.timeout(0.75):
            pool = await create_pool(redis_settings())
            job = await pool.enqueue_job(
                "process_document",
                document_id,
                filename,
                content,
                _job_id=f"{get_settings().ingestion_queue}:document:{document_id}",
                _queue_name=get_settings().ingestion_queue,
                _expires=7 * 24 * 60 * 60,
            )
            if job is None:
                raise QueueUnavailable()
    except Exception:  # noqa: BLE001 - sanitize errors at the service boundary
        raise QueueUnavailable() from None
    finally:
        if pool is not None:
            try:
                async with asyncio.timeout(0.1):
                    await pool.aclose()
            except Exception:  # noqa: BLE001 - sanitize errors at the service boundary
                logging.getLogger(__name__).warning("Queue connection cleanup failed")
