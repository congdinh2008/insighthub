"""Backend-enforced three-tier policy and one-use scale approvals."""

import hashlib
import json
import re
import secrets
import time
from typing import Any, Awaitable, cast

from redis.asyncio import Redis

from .queue import PREFIX

SCALE = re.compile(r"\bscale\s+(?:api|insighthub-api)\s+(?:to\s+)?(\d+)\b", re.I)
CONFIRM = re.compile(r"\bconfirm\s+([A-Za-z0-9_-]{20,80})\b", re.I)
DESTRUCTIVE = re.compile(r"\b(delete|drop|destroy|wipe|remove|xóa|xoá)\b", re.I)
CONSUME = """
local raw = redis.call('GET', KEYS[1])
if not raw then return false end
local r = cjson.decode(raw)
if r.workspace ~= ARGV[1] or r.channel ~= ARGV[2]
   or r.approver ~= ARGV[3] or r.thread ~= ARGV[4]
   or r.expires_at < tonumber(ARGV[5]) then return false end
redis.call('DEL', KEYS[1])
redis.call('SET', KEYS[2], raw, 'EX', 86400)
return raw
"""


def route(question: str) -> tuple[str, int | str | None]:
    text = re.sub(r"<@[A-Z0-9]+>", " ", question).strip()
    if DESTRUCTIVE.search(text):
        return "destructive", None
    match = CONFIRM.fullmatch(text)
    if match:
        return "confirm", match.group(1)
    match = SCALE.fullmatch(text)
    if match:
        replicas = int(match.group(1))
        return ("scale", replicas) if 1 <= replicas <= 5 else ("denied", None)
    if re.search(r"\b(scale|confirm)\b", text, re.I):
        return "denied", None
    lowered = text.casefold()
    if any(x in lowered for x in ("pod", "crashloop", "container", "workload")):
        return "pods", None
    if any(x in lowered for x in ("ingest", "document", "doc", "tài liệu", "nap lieu")):
        return "ingestion", None
    if any(x in lowered for x in ("health", "healthy", "khỏe", "khoe", "tình trạng", "status")):
        return "health", None
    return "unknown", None


def approval_key(token: str) -> str:
    return PREFIX + "approval:" + hashlib.sha256(token.encode()).hexdigest()


async def request_approval(redis: Redis, *, workspace: str, channel: str,
                           thread: str, requester: str, approver: str,
                           replicas: int, target_uid: str,
                           resource_version: str, current_replicas: int,
                           namespace: str, cluster: str) -> tuple[str, dict[str, Any]]:
    if not approver or not (1 <= replicas <= 5):
        raise ValueError("approver and bounded replicas required")
    token = secrets.token_urlsafe(24)
    record: dict[str, Any] = {
        "workspace": workspace, "channel": channel, "thread": thread,
        "requester": requester, "approver": approver, "action": "scale_api",
        "replicas": replicas, "target": "insighthub-api", "target_uid": target_uid,
        "resource_version": resource_version, "current_replicas": current_replicas,
        "namespace": namespace, "cluster": cluster,
        "operation_id": secrets.token_hex(16), "expires_at": int(time.time()) + 60,
    }
    await redis.set(approval_key(token), json.dumps(record), ex=60, nx=True)
    return token, record


async def consume_approval(redis: Redis, token: str, *, workspace: str,
                           channel: str, thread: str, approver: str) -> dict[str, Any] | None:
    key = approval_key(token)
    raw = await cast(Awaitable[bytes | None], redis.eval(
        CONSUME, 2, key, PREFIX + "consumed:" + key.rsplit(":", 1)[1],
        workspace, channel, approver, thread, str(int(time.time()))))
    return json.loads(raw) if raw else None
