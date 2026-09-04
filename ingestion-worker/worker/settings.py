from arq.connections import RedisSettings

from app.core.config import get_settings
from worker.tasks import ingest_document


class Settings:
    functions = [ingest_document]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 5
    max_tries = 3