"""Bounded ARQ submission. Job identity protects concurrent/ambiguous submissions."""

import asyncio

from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job, JobStatus
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.errors import DocumentConflict, QueueUnavailable


def redis_settings() -> RedisSettings:
    settings = RedisSettings.from_dsn(get_settings().redis_url)
    settings.conn_timeout = 1
    settings.conn_retries = 0
    return settings


def job_id(document_id: int) -> str:
    return f"ingestion:{document_id}"


async def enqueue(
    document_id: int, filename: str, content: bytes, *, require_new: bool = False
) -> bool:
    pool = None
    try:
        pool = await create_pool(
            redis_settings(), default_queue_name=get_settings().queue_name
        )
        job = await asyncio.wait_for(
            pool.enqueue_job(
                "ingest",
                document_id,
                filename,
                content,
                _job_id=job_id(document_id),
                _expires=86400,
            ),
            timeout=1,
        )
        if job is not None:
            return True
        if require_new:
            # A failed DB row can be observed before ARQ removes its finishing job.
            # Returning 202 here would strand it pending without a fresh attempt.
            raise DocumentConflict()
        # Existing active job is accepted only when resolving the initial submission.
        status = await asyncio.wait_for(
            Job(
                job_id(document_id), pool, _queue_name=get_settings().queue_name
            ).status(),
            timeout=1,
        )
        return status in {JobStatus.queued, JobStatus.deferred, JobStatus.in_progress}
    except (TimeoutError, RedisError, OSError):
        # A lost enqueue response may still have committed. For an initial upload,
        # the identity is new. A manual retry could instead observe an old finishing
        # job, so ambiguous acceptance there must fail safely rather than claim 202.
        if pool is not None and not require_new:
            try:
                status = await asyncio.wait_for(
                    Job(
                        job_id(document_id), pool, _queue_name=get_settings().queue_name
                    ).status(),
                    timeout=1,
                )
                if status in {
                    JobStatus.queued,
                    JobStatus.deferred,
                    JobStatus.in_progress,
                }:
                    return True
            except (TimeoutError, RedisError, OSError):
                pass
        raise QueueUnavailable() from None
    finally:
        if pool is not None:
            await pool.aclose()


def enqueue_document(
    document_id: int, filename: str, content: bytes, *, require_new: bool = False
) -> None:
    """Called only from a sync FastAPI handler (threadpool), never its event loop."""
    if not asyncio.run(
        enqueue(document_id, filename, content, require_new=require_new)
    ):
        raise QueueUnavailable()


async def queue_healthcheck() -> bool:
    pool = None
    try:
        pool = await create_pool(redis_settings())
        return bool(await asyncio.wait_for(pool.ping(), timeout=1))
    except (TimeoutError, RedisError, OSError):
        return False
    finally:
        if pool is not None:
            await pool.aclose()
