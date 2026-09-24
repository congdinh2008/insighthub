"""Day 05 behavioral contract against the real Redis inbox and HTTP app."""

import asyncio
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from redis.asyncio import Redis

ROOT = Path(os.environ.get("INSIGHTHUB_REPO_ROOT", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(ROOT / "chatops-bot"))

from app.config import Settings  # noqa: E402
from app.main import app  # noqa: E402
from app.permissions import consume_approval, request_approval  # noqa: E402
from app.queue import READY, accept, finish, next_job, recover  # noqa: E402
from app.worker import process  # noqa: E402

RUN_ID = os.environ.get("INSIGHTHUB_VERIFY_RUN_ID", uuid.uuid4().hex)
OBSERVATIONS = Path(os.environ.get("INSIGHTHUB_VERIFY_OBSERVATIONS", "/tmp/day5-observations.json"))
AUDIT = OBSERVATIONS.with_name("day5-test-audit-" + RUN_ID + ".jsonl")
REDIS_URL = os.environ.get("CHATOPS_REDIS_URL", "redis://127.0.0.1:16380/0").rsplit("/", 1)[0] + "/14"


def settings() -> Settings:
    return replace(Settings.from_env(), signing_secret="test-signing-secret", bot_token="test-bot-token",
                   channel_id="C_TEST", approver_user_id="U_APPROVER", audit_path=str(AUDIT),
                   redis_url=REDIS_URL, kubeconfig_scale="test-scale-kubeconfig")


def event(text: str, user: str = "U_REQUESTER") -> dict:
    return {"workspace": "T0C35P86Z1D", "channel": "C_TEST", "thread": "123.45",
            "event_id": uuid.uuid4().hex, "user": user, "text": text}


@pytest.fixture(scope="session", autouse=True)
def export_audit():
    yield
    rows = [json.loads(line) for line in AUDIT.read_text().splitlines()] if AUDIT.exists() else []
    OBSERVATIONS.parent.mkdir(parents=True, exist_ok=True)
    OBSERVATIONS.write_text(json.dumps({"run_id": RUN_ID, "events": rows}))


def test_permission_denied():
    async def check():
        client = Redis.from_url(REDIS_URL)
        try:
            reply = await process(event("delete namespace insighthub-dev"), settings(), client)
            assert "Chỉ hỗ trợ" in reply
        finally:
            await client.aclose()
    asyncio.run(check())
    assert any(row["decision"] == "denied" and row["action"] == "destructive"
               for row in map(json.loads, AUDIT.read_text().splitlines()))


def test_approval_required(monkeypatch):
    async def inspection(_):
        return {"uid": "uid-realistic", "resource_version": "123", "replicas": 1}
    monkeypatch.setattr("app.worker.inspect_api", inspection)

    async def check():
        client = Redis.from_url(REDIS_URL)
        try:
            reply = await process(event("scale api to 2"), settings(), client)
            assert "Chưa thay đổi" in reply and "confirm" in reply
        finally:
            await client.aclose()
    asyncio.run(check())
    assert any(row["decision"] == "approval_required" and row["action"] == "scale_api"
               for row in map(json.loads, AUDIT.read_text().splitlines()))


def test_approval_bound_to_action():
    async def check():
        client = Redis.from_url(REDIS_URL)
        try:
            thread = uuid.uuid4().hex
            token, _ = await request_approval(client, workspace="T0C35P86Z1D", channel="C_TEST",
                thread=thread, requester="U_REQUESTER", approver="U_APPROVER", replicas=2,
                target_uid="uid-realistic", resource_version="123", current_replicas=1,
                namespace="insighthub-dev", cluster="kind-insighthub-local")
            for binding in ({"workspace": "T_OTHER"}, {"channel": "C_OTHER"},
                            {"thread": "wrong"}, {"approver": "U_ATTACKER"}):
                context = dict(workspace="T0C35P86Z1D", channel="C_TEST",
                               thread=thread, approver="U_APPROVER")
                context.update(binding)
                assert await consume_approval(client, token, **context) is None
            valid = await consume_approval(client, token, workspace="T0C35P86Z1D",
                                           channel="C_TEST", thread=thread, approver="U_APPROVER")
            assert valid and valid["target"] == "insighthub-api" and valid["replicas"] == 2
            assert await consume_approval(client, token, workspace="T0C35P86Z1D",
                                          channel="C_TEST", thread=thread, approver="U_APPROVER") is None
        finally:
            await client.aclose()
    asyncio.run(check())


def test_duplicate_event():
    async def check():
        client = Redis.from_url(REDIS_URL)
        try:
            row = event("api healthy?")
            results = await asyncio.gather(*(accept(client, row["workspace"], row["event_id"], row)
                                             for _ in range(10)))
            assert results.count(True) == 1 and results.count(False) == 9
            jobs = await client.lrange(READY, 0, -1)
            assert sum(json.loads(item)["event_id"] == row["event_id"] for item in jobs) == 1
            await client.lrem(READY, 0, json.dumps(row, ensure_ascii=False,
                                                   separators=(",", ":")))
        finally:
            await client.aclose()
    asyncio.run(check())


def test_invalid_signature():
    async def check():
        original_settings, original_redis = app.state.settings, app.state.redis
        app.state.settings = settings()
        app.state.redis = Redis.from_url(REDIS_URL)
        try:
            body = json.dumps({"type": "url_verification", "challenge": "secret-challenge"}).encode()
            timestamp = str(int(time.time()))
            signature = "v0=" + hmac.new(b"test-signing-secret", b"v0:" + timestamp.encode() + b":" + body,
                                          hashlib.sha256).hexdigest()
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                         base_url="http://test") as client:
                assert (await client.post("/slack/events", content=body)).status_code == 401
                headers = {"X-Slack-Request-Timestamp": timestamp, "X-Slack-Signature": signature}
                good = await client.post("/slack/events", content=body, headers=headers)
                assert good.status_code == 200 and good.json()["challenge"] == "secret-challenge"
                stale = {**headers, "X-Slack-Request-Timestamp": str(int(timestamp) - 301)}
                assert (await client.post("/slack/events", content=body, headers=stale)).status_code == 401
                assert (await client.post("/slack/events", content=body + b" ", headers=headers)).status_code == 401
        finally:
            await app.state.redis.aclose()
            app.state.settings, app.state.redis = original_settings, original_redis
    asyncio.run(check())


def test_ack_before_processing_and_recovery():
    async def check():
        original_settings, original_redis = app.state.settings, app.state.redis
        app.state.settings = settings()
        app.state.redis = Redis.from_url(REDIS_URL)
        try:
            row = event("api healthy?")
            payload = {"type": "event_callback", "api_app_id": "A0C3EU2GD35",
                       "team_id": row["workspace"], "event_id": row["event_id"],
                       "event": {"type": "app_mention", "user": row["user"],
                                 "channel": row["channel"], "text": row["text"], "ts": "123.45"}}
            body = json.dumps(payload).encode()
            timestamp = str(int(time.time()))
            signature = "v0=" + hmac.new(b"test-signing-secret", b"v0:" + timestamp.encode() + b":" + body,
                                          hashlib.sha256).hexdigest()
            headers = {"X-Slack-Request-Timestamp": timestamp, "X-Slack-Signature": signature}
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                         base_url="http://test") as client:
                started = time.monotonic()
                first = await client.post("/slack/events", content=body, headers=headers)
                elapsed = time.monotonic() - started
                second = await client.post("/slack/events", content=body, headers=headers)
            assert first.status_code == 200 and first.json()["duplicate"] is False
            assert elapsed < 3
            assert second.status_code == 200 and second.json()["duplicate"] is True
            leased = await next_job(app.state.redis, timeout=1)
            assert leased is not None and json.loads(leased)["event_id"] == row["event_id"]
            assert await recover(app.state.redis) >= 1
            recovered = await next_job(app.state.redis, timeout=1)
            assert recovered == leased
            await finish(app.state.redis, recovered)
        finally:
            await app.state.redis.aclose()
            app.state.settings, app.state.redis = original_settings, original_redis
    asyncio.run(check())
