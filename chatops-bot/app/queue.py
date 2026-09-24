"""Redis inbox: enqueue and dedup in one script; worker leases survive restart."""

import json
from typing import Any, Awaitable, cast

from redis.asyncio import Redis

PREFIX = "insighthub:chatops:"
READY = PREFIX + "ready"
PROCESSING = PREFIX + "processing"
DEAD = PREFIX + "dead"
ACCEPT = """
if redis.call('EXISTS', KEYS[1]) == 1 then return 0 end
redis.call('LPUSH', KEYS[2], ARGV[1])
redis.call('SET', KEYS[1], '1', 'EX', 172800)
return 1
"""
REQUEUE = """
if redis.call('LREM', KEYS[1], 1, ARGV[1]) ~= 1 then return 0 end
redis.call('LPUSH', KEYS[2], ARGV[2])
return 1
"""


async def accept(redis: Redis, workspace: str, event_id: str,
                 event: dict[str, Any]) -> bool:
    payload = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    result = await cast(Awaitable[int], redis.eval(
        ACCEPT, 2, PREFIX + "event:" + workspace + ":" + event_id, READY, payload))
    return bool(result)


async def next_job(redis: Redis, timeout: int = 2) -> bytes | None:
    return await cast(Awaitable[bytes | None], redis.brpoplpush(
        READY, PROCESSING, timeout=timeout))


async def finish(redis: Redis, payload: bytes) -> None:
    await cast(Awaitable[int], redis.lrem(PROCESSING, 1, payload.decode()))


async def retry(redis: Redis, old: bytes, event: dict[str, Any]) -> bool:
    new = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    return bool(await cast(Awaitable[int], redis.eval(
        REQUEUE, 2, PROCESSING, READY, old.decode(), new)))


async def deadletter(redis: Redis, old: bytes) -> bool:
    return bool(await cast(Awaitable[int], redis.eval(
        REQUEUE, 2, PROCESSING, DEAD, old.decode(), old.decode())))


async def recover(redis: Redis) -> int:
    count = 0
    while True:
        job = await cast(Awaitable[bytes | None], redis.rpoplpush(PROCESSING, READY))
        if job is None:
            return count
        count += 1
