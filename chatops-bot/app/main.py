"""InsightHub ChatOps Bot — FastAPI application."""
import hashlib
import hmac
import json
import logging
import os
import re
import time

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from slack_sdk.web.async_client import AsyncWebClient

from app.handler import handle_question

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("chatops-bot")

app = FastAPI(title="InsightHub ChatOps Bot", version="1.0.0")

SLACK_SIGNING_SECRET: str = os.getenv("SLACK_SIGNING_SECRET", "")
SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")

_PROCESSED_EVENTS: set[str] = set()  # in-process dedup (resets on restart)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok", "service": "chatops-bot"}


# ---------------------------------------------------------------------------
# Slack Events
# ---------------------------------------------------------------------------

@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    """Receive Slack events, verify signature, dispatch to background handler."""
    # Read raw body BEFORE any parsing (required for HMAC verification)
    body: bytes = await request.body()

    # Verify x-slack-signature using HMAC-SHA256
    if SLACK_SIGNING_SECRET:
        verify_slack_signature(request.headers, body, SLACK_SIGNING_SECRET)

    payload = _parse_json(body)

    # Slack URL-verification handshake (first-time setup)
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    event: dict = payload.get("event", {})
    event_type: str = event.get("type", "")

    if event_type not in ("app_mention",):
        return {"ok": True}

    # Deduplicate retried events
    event_id: str = payload.get("event_id", "")
    if event_id:
        if event_id in _PROCESSED_EVENTS:
            return {"ok": True}
        _PROCESSED_EVENTS.add(event_id)

    user_id: str = event.get("user", "unknown")
    channel: str = event.get("channel", "")
    thread_ts: str = event.get("thread_ts") or event.get("ts", "")
    raw_text: str = event.get("text", "")
    question: str = _strip_bot_mention(raw_text)

    if not question:
        return {"ok": True}

    logger.info("Question from %s in %s: %.120s", user_id, channel, question)

    # Return 200 immediately — Slack will retry if we take > 3s
    background_tasks.add_task(_process_and_reply, question, user_id, channel, thread_ts)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Signature verification (exported for testing)
# ---------------------------------------------------------------------------

def verify_slack_signature(headers, body: bytes, signing_secret: str) -> None:
    """Verify X-Slack-Signature header; raise HTTPException(401) if invalid.

    Also rejects requests with timestamps older than 5 minutes (replay defense).
    Uses x-slack-signature header via HMAC-SHA256.
    """
    timestamp: str = headers.get("x-slack-request-timestamp", "")
    slack_sig: str = headers.get("x-slack-signature", "")

    if not timestamp or not slack_sig:
        raise HTTPException(status_code=401, detail="Missing Slack signature headers")

    try:
        req_time = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp format")

    # Replay attack defense: reject requests older than 5 minutes
    if abs(time.time() - req_time) > 300:
        raise HTTPException(status_code=401, detail="Request timestamp too old — possible replay attack")

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected = "v0=" + hmac.new(
        signing_secret.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, slack_sig):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json(body: bytes) -> dict:
    try:
        return json.loads(body)
    except Exception:
        return {}


def _strip_bot_mention(text: str) -> str:
    """Remove <@BOTID> mention prefix from message text."""
    return re.sub(r"<@[A-Z0-9]+>\s*", "", text).strip()


async def _process_and_reply(
    question: str, user_id: str, channel: str, thread_ts: str
) -> None:
    """Background task: call handler and post answer back to Slack."""
    try:
        answer, needs_confirm, token = await handle_question(question, user_id)
        logger.info("Answer for %s (needs_confirm=%s): %.200s", user_id, needs_confirm, answer)

        if SLACK_BOT_TOKEN and channel:
            slack = AsyncWebClient(token=SLACK_BOT_TOKEN)
            await slack.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=answer,
                mrkdwn=True,
            )
        else:
            logger.info("No SLACK_BOT_TOKEN — skipping Slack post")
    except Exception as exc:
        logger.error("Error processing question from %s: %s", user_id, exc, exc_info=True)
