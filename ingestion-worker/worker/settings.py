"""ARQ worker configuration. Reuses api/app's Settings - one identity, one validation."""

import asyncio

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.db import close_pool, initialize_database

from worker.logging_config import configure_logging
from worker.tasks import ingest_document


async def startup(ctx) -> None:
    configure_logging(get_settings().log_level)
    await asyncio.to_thread(initialize_database)


async def shutdown(ctx) -> None:
    await asyncio.to_thread(close_pool)


class WorkerSettings:
    functions = [ingest_document]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    on_startup = startup
    on_shutdown = shutdown
