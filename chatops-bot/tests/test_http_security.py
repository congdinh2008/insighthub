"""Signed HTTP boundary tests; no Slack network calls."""
import asyncio
import hashlib
import hmac
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app  # noqa: E402
from app.security import verify_request  # noqa: E402


def signed(body, timestamp):
    stamp = str(timestamp)
    digest = hmac.new(b"test", b"v0:" + stamp.encode() + b":" + body, hashlib.sha256).hexdigest()
    return {"X-Slack-Request-Timestamp": stamp, "X-Slack-Signature": "v0=" + digest}


@pytest.mark.parametrize("offset,expected", [(-301, False), (-300, True), (0, True), (300, True), (301, False)])
def test_timestamp_window_uses_valid_signature(offset, expected):
    body = b'{"type":"url_verification","challenge":"hello"}'
    assert verify_request(body, signed(body, 1000000 + offset), "test", now=1000000) is expected


@pytest.mark.parametrize("update,status", [
    ({"team_id": "T_OTHER"}, 403), ({"api_app_id": "A_OTHER"}, 403),
    ({"event_id": ""}, 400), ({"event": {"type": "app_mention", "user": "U", "channel": "C", "text": "health", "ts": "1.2", "thread_ts": {"bad": True}}}, 400),
])
def test_bad_envelope_never_enqueues(monkeypatch, update, status):
    async def forbidden(*args):
        raise AssertionError("must not enqueue invalid event")
    monkeypatch.setattr("app.main.accept", forbidden)
    monkeypatch.setattr(app.state, "settings", replace(app.state.settings, signing_secret="test", workspace_id="T", app_id="A", channel_id="C"))
    payload = dict(type="event_callback", team_id="T", api_app_id="A", event_id="Ev1",
                   event=dict(type="app_mention", user="U", channel="C", text="health", ts="1.2"))
    payload.update(update)
    async def check():
        body = json.dumps(payload).encode()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            result = await client.post("/slack/events", content=body, headers=signed(body, int(time.time())))
            assert result.status_code == status
    asyncio.run(check())


def test_oversized_http_body_rejected_before_json():
    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.post("/slack/events", content=b"x" * 65537)).status_code == 413
    asyncio.run(check())


def test_queue_unavailable_is_retriable_not_success(monkeypatch):
    async def failed(*args):
        raise ConnectionError()
    monkeypatch.setattr("app.main.accept", failed)
    monkeypatch.setattr(app.state, "settings", replace(app.state.settings, signing_secret="test", workspace_id="T", app_id="A", channel_id="C"))
    async def check():
        body = json.dumps(dict(type="event_callback", team_id="T", api_app_id="A", event_id="Ev1",
                               event=dict(type="app_mention", user="U", channel="C", text="health", ts="1.2"))).encode()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            result = await client.post("/slack/events", content=body, headers=signed(body, int(time.time())))
            assert result.status_code == 503
    asyncio.run(check())
