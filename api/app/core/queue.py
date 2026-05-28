"""
InsightHub API — ARQ job queue

Module-level singleton pattern: pool được khởi tạo trong lifespan của FastAPI,
sau đó các router lấy qua get_arq_pool().
"""
import logging

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings

logger = logging.getLogger("insighthub.queue")

_arq_pool: ArqRedis | None = None


async def open_arq_pool() -> None:
    global _arq_pool
    settings = get_settings()
    _arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    logger.info("ARQ Redis pool opened: %s", settings.redis_url)


def get_arq_pool() -> ArqRedis | None:
    return _arq_pool


async def close_arq_pool() -> None:
    global _arq_pool
    if _arq_pool is not None:
        await _arq_pool.aclose()
        _arq_pool = None
        logger.info("ARQ Redis pool closed")
