"""Redis/ARQ queue used by the API to enqueue ingestion jobs."""
from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings

_redis: ArqRedis | None = None


async def get_queue() -> ArqRedis:
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _redis


async def close_queue() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None