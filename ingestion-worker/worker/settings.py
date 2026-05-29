import os

from arq.connections import RedisSettings

from app.core.db import close_pool
from worker.tasks import ingest_document


async def on_shutdown(ctx):
    close_pool()


class WorkerSettings:
    functions = [ingest_document]
    redis_settings = RedisSettings.from_dsn(
        os.environ.get("REDIS_URL", "redis://redis:6379")
    )
    max_jobs = 4
    on_shutdown = on_shutdown
