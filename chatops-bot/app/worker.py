"""Durable ChatOps worker: fixed intents, policy gate, bounded retry, Slack reply."""

import asyncio
import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from .audit import record
from .config import Settings
from .executor import ScaleError, inspect_api, scale_api
from .intents import answer
from .model import summarize
from .permissions import consume_approval, request_approval, route
from .queue import PREFIX, deadletter, finish, next_job, recover, retry

logger = logging.getLogger("chatops.worker")


async def heartbeat(redis: Redis) -> None:
    while True:
        await redis.set(PREFIX + "worker:heartbeat", "1", ex=10)
        await asyncio.sleep(3)


async def process(event: dict[str, Any], settings: Settings, redis: Redis) -> str:
    event_id = str(event["event_id"])
    user = str(event["user"])
    workspace = str(event["workspace"])
    channel = str(event["channel"])
    thread = str(event["thread"])
    intent, arg = route(str(event["text"]))
    if intent in {"health", "pods", "ingestion"}:
        record(settings.audit_path, event_id=event_id, user=user, action=intent,
               decision="allowed", workspace_id=workspace, intent=intent)
        try:
            result, calls = await asyncio.wait_for(answer(intent, settings), timeout=30)
            for tool, summary in calls:
                record(settings.audit_path, event_id=event_id, user=user, action="tool_call",
                       decision="allowed", workspace_id=workspace, tool=tool,
                       result_summary=summary)
            model_text = await summarize(result, settings)
            if model_text:
                result += "\nNhận định AI (tham khảo): " + model_text
                record(settings.audit_path, event_id=event_id, user=user,
                       action="model_summary", decision="allowed", outcome="generated")
        except Exception as exc:
            result = f"InsightHub {settings.namespace}: chưa thể trả lời {intent} vì nguồn dữ liệu lỗi. Vui lòng kiểm lại sau."
            record(settings.audit_path, event_id=event_id, user=user, action=intent,
                   decision="denied", outcome=type(exc).__name__)
    elif intent == "scale" and isinstance(arg, int):
        if not settings.approver_user_id or not settings.kubeconfig_scale:
            record(settings.audit_path, event_id=event_id, user=user, action="scale_api",
                   decision="denied", outcome="approval_or_scale_identity_unavailable")
            result = "Chưa cấu hình approver hoặc scale identity. Không thực hiện scale."
        else:
            try:
                current = await inspect_api(settings)
                token, approval = await request_approval(
                    redis, workspace=workspace, channel=channel, thread=thread,
                    requester=user, approver=settings.approver_user_id, replicas=arg,
                    target_uid=current["uid"], resource_version=current["resource_version"],
                    current_replicas=current["replicas"], namespace=settings.namespace,
                    cluster=settings.cluster_context)
                record(settings.audit_path, event_id=event_id, user=user, action="scale_api",
                       decision="approval_required", operation_id=approval["operation_id"],
                       target="insighthub-api", replicas=arg, current_replicas=current["replicas"])
                result = (f"Yêu cầu scale insighthub-api {current['replicas']} -> {arg} ở {settings.namespace}. "
                          f"Chưa thay đổi. Người duyệt dùng `@bot confirm {token}` trong thread này trong 60 giây.")
            except Exception as exc:
                record(settings.audit_path, event_id=event_id, user=user, action="scale_api",
                       decision="denied", outcome=type(exc).__name__)
                result = "Không tạo được yêu cầu scale; chưa thay đổi deployment."
    elif intent == "confirm" and isinstance(arg, str):
        confirmed = await consume_approval(redis, arg, workspace=workspace, channel=channel,
                                           thread=thread, approver=user)
        if confirmed is None:
            record(settings.audit_path, event_id=event_id, user=user, action="scale_api",
                   decision="denied", outcome="approval_invalid_expired_or_replayed")
            result = "Confirmation không hợp lệ, hết hạn hoặc đã dùng. Không scale."
        else:
            # Durable audit is a precondition of mutation.
            record(settings.audit_path, event_id=event_id, user=user, action="scale_api",
                   decision="allowed", operation_id=confirmed["operation_id"],
                   target="insighthub-api", replicas=confirmed["replicas"])
            try:
                after = await scale_api(settings, confirmed)
                record(settings.audit_path, event_id=event_id, user=user, action="scale_api_result",
                       decision="allowed", operation_id=confirmed["operation_id"],
                       outcome="verified", replicas=after["replicas"])
                result = (f"Đã scale insighthub-api tới {after['replicas']} replicas "
                          f"ở {settings.namespace}. Kiểm readiness và đối chiếu với baseline demo.")
            except (ScaleError, TimeoutError, OSError, ValueError, KeyError):
                record(settings.audit_path, event_id=event_id, user=user, action="scale_api_result",
                       decision="denied", operation_id=confirmed["operation_id"],
                       outcome="unknown_or_failed")
                result = "Scale không xác nhận thành công. Kiểm deployment trước khi tạo yêu cầu mới."
    else:
        record(settings.audit_path, event_id=event_id, user=user, action=intent,
               decision="denied", outcome="unsupported_or_destructive")
        result = "Chỉ hỗ trợ đọc health, ingestion hôm nay, pods lỗi và scale API có approval."
    return result


async def run() -> None:
    settings = Settings.from_env()
    if not settings.bot_token or not settings.signing_secret:
        raise SystemExit("Slack credentials required")
    redis = Redis.from_url(settings.redis_url, decode_responses=False,
                           socket_connect_timeout=2, socket_timeout=3)
    slack = AsyncWebClient(token=settings.bot_token)
    await recover(redis)
    heartbeat_task = asyncio.create_task(heartbeat(redis))
    try:
        while True:
            raw = await next_job(redis)
            if raw is None:
                continue
            event = json.loads(raw)
            done_key = PREFIX + "done:" + event["workspace"] + ":" + event["event_id"]
            reply_key = PREFIX + "reply:" + event["workspace"] + ":" + event["event_id"]
            if await redis.exists(done_key):
                await finish(redis, raw)
                continue
            try:
                cached = await redis.get(reply_key)
                result = cached.decode() if cached else await process(event, settings, redis)
                if cached is None:
                    await redis.set(reply_key, result, ex=172800)
                await slack.chat_postMessage(channel=str(event["channel"]),
                                             thread_ts=str(event["thread"]), text=result)
                await redis.set(done_key, "1", ex=172800)
                await finish(redis, raw)
            except (SlackApiError, RedisError, OSError, TimeoutError, ConnectionError) as exc:
                event["attempts"] = int(event.get("attempts", 0)) + 1
                record(settings.audit_path, event_id=str(event["event_id"]),
                       user=str(event["user"]), action="delivery", decision="denied",
                       outcome=type(exc).__name__, attempt=event["attempts"])
                if event["attempts"] < 4:
                    retry_after = 0
                    if isinstance(exc, SlackApiError) and exc.response.status_code == 429:
                        retry_after = int(exc.response.headers.get("Retry-After", "1"))
                    await asyncio.sleep(min(max(retry_after, 2 ** event["attempts"]), 30))
                    await retry(redis, raw, event)
                else:
                    await deadletter(redis, raw)
            except Exception as exc:
                logger.error("job failed: %s", type(exc).__name__)
                record(settings.audit_path, event_id=str(event["event_id"]),
                       user=str(event["user"]), action="processing", decision="denied",
                       outcome=type(exc).__name__)
                await deadletter(redis, raw)
    finally:
        heartbeat_task.cancel()
        await asyncio.gather(heartbeat_task, return_exceptions=True)
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run())
