"""Authenticated Slack Events HTTP intake; no MCP or model work before ACK."""

import asyncio
import json

from fastapi import FastAPI, HTTPException, Request
from redis.asyncio import Redis

from .config import Settings
from .queue import PREFIX, accept
from .security import verify_request

app = FastAPI(title="InsightHub Day 05 ChatOps", version="1.0.0")
app.state.settings = Settings.from_env()
app.state.redis = Redis.from_url(app.state.settings.redis_url, decode_responses=False,
                                 socket_connect_timeout=1, socket_timeout=1)


@app.get("/healthz")
async def health() -> dict[str, object]:
    settings: Settings = app.state.settings
    configured = all((settings.signing_secret, settings.bot_token, settings.channel_id,
                      settings.app_id, settings.workspace_id, settings.bot_user_id,
                      settings.approver_user_id, settings.mcp_config, settings.kubeconfig_scale))
    try:
        redis_ready = bool(await app.state.redis.ping())
        worker_ready = bool(await app.state.redis.exists(PREFIX + "worker:heartbeat"))
    except Exception:
        redis_ready = worker_ready = False
    ready = configured and redis_ready and worker_ready
    return {"status": "ok" if ready else "not_ready", "ready": ready,
            "transport": "http", "worker_ready": worker_ready}


@app.post("/slack/events")
async def slack_events(request: Request) -> dict[str, object]:
    settings: Settings = app.state.settings
    # Bound memory before authenticating an untrusted public HTTP body.
    chunks = bytearray()
    async for chunk in request.stream():
        chunks.extend(chunk)
        if len(chunks) > 64 * 1024:
            raise HTTPException(status_code=413, detail="payload too large")
    body = bytes(chunks)
    if not verify_request(body, request.headers, settings.signing_secret):
        raise HTTPException(status_code=401, detail="invalid Slack signature or timestamp")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        raise HTTPException(status_code=400, detail="invalid JSON") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid payload")
    if payload.get("api_app_id") not in (None, settings.app_id):
        raise HTTPException(status_code=403, detail="wrong app")
    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge")
        if not isinstance(challenge, str) or not challenge:
            raise HTTPException(status_code=400, detail="invalid challenge")
        return {"challenge": challenge}
    if payload.get("type") != "event_callback":
        return {"ok": True, "ignored": True}
    if payload.get("team_id") != settings.workspace_id:
        raise HTTPException(status_code=403, detail="wrong workspace")
    event = payload.get("event")
    if not isinstance(event, dict) or event.get("type") != "app_mention":
        return {"ok": True, "ignored": True}
    user, channel, text, stamp = (event.get(k) for k in ("user", "channel", "text", "ts"))
    if (event.get("bot_id") or event.get("subtype") or not isinstance(user, str)
            or user == settings.bot_user_id or not isinstance(channel, str)
            or channel != settings.channel_id or not isinstance(text, str)
            or not isinstance(stamp, str)):
        return {"ok": True, "ignored": True}
    event_id = payload.get("event_id")
    if (not isinstance(event_id, str) or not event_id or len(event_id) > 128
            or len(text) > 2048 or not user or not stamp
            or not isinstance(event.get("thread_ts", stamp), str)):
        raise HTTPException(status_code=400, detail="invalid event")
    normalized = {
        "workspace": settings.workspace_id, "event_id": event_id,
        "user": user, "channel": channel, "thread": event.get("thread_ts") or stamp,
        "text": text, "attempts": 0,
    }
    try:
        fresh = await asyncio.wait_for(
            accept(app.state.redis, settings.workspace_id, event_id, normalized), timeout=2)
    except Exception:
        raise HTTPException(status_code=503, detail="event inbox unavailable") from None
    return {"ok": True, "duplicate": not fresh}
