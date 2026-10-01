import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from app.worker import heartbeat, supervise
from redis.exceptions import TimeoutError as RedisTimeoutError


def test_supervisor_reconnects_after_redis_timeout_and_preserves_cancellation():
    async def exercise():
        with (
            patch("app.worker.run", new_callable=AsyncMock) as run,
            patch("app.worker.asyncio.sleep", new_callable=AsyncMock) as sleep,
        ):
            run.side_effect = [RedisTimeoutError("synthetic"), asyncio.CancelledError()]
            with pytest.raises(asyncio.CancelledError):
                await supervise()
            assert run.await_count == 2
            sleep.assert_awaited_once_with(2)

    asyncio.run(exercise())


def test_heartbeat_recovers_without_refreshing_ttl_during_outage():
    async def exercise():
        redis = AsyncMock()
        redis.set.side_effect = [RedisTimeoutError("synthetic"), None]
        with patch("app.worker.asyncio.sleep", new_callable=AsyncMock) as sleep:
            sleep.side_effect = [None, asyncio.CancelledError()]
            with pytest.raises(asyncio.CancelledError):
                await heartbeat(redis)
        assert redis.set.await_count == 2
        assert redis.set.await_args.kwargs == {"ex": 10}

    asyncio.run(exercise())
