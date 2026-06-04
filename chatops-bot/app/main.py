import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import time

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
import httpx
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

TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_SECRET_TOKEN: str = os.getenv("TELEGRAM_SECRET_TOKEN", "")
CHATOPS_DEFAULT_PLATFORM: str = os.getenv("CHATOPS_DEFAULT_PLATFORM", "telegram").lower()

_PROCESSED_EVENTS: set[str] = set()  # in-process dedup (resets on restart)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/healthz")
async def health() -> dict:
    return {"status": "ok", "service": "chatops-bot"}


# ---------------------------------------------------------------------------
# Telegram Integration
# ---------------------------------------------------------------------------

_telegram_polling_task = None


async def send_telegram_message(chat_id: int, text: str, reply_to_message_id: int | None = None) -> None:
    """Send message to Telegram with standard Markdown parsing. Fallback to plain text on error."""
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set — skipping Telegram post")
        return

    url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_to_message_id is not None:
        payload["reply_parameters"] = {"message_id": reply_to_message_id}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, timeout=10.0)
            if resp.status_code == 400 and "can't parse" in resp.text:
                logger.warning("Telegram Markdown parse failed, falling back to plain text")
                payload.pop("parse_mode", None)
                resp = await client.post(url, json=payload, timeout=10.0)
            if resp.status_code != 200:
                logger.error("Failed to send Telegram message: status=%d, body=%s", resp.status_code, resp.text)
        except Exception as exc:
            logger.error("Error sending Telegram message: %s", exc)


async def process_telegram_update(update: dict) -> None:
    """Process a single Telegram update payload."""
    message = update.get("message")
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    text = message.get("text", "")
    user_info = message.get("from", {})
    user_id = user_info.get("username") or str(user_info.get("id", "unknown"))

    if not text or chat_id is None:
        return

    # Handle /start or /help command
    if text.startswith(("/start", "/help")):
        welcome = (
            "Xin chào! Tôi là InsightHub ops bot. Hãy hỏi tôi về hệ thống.\n\n"
            "Ví dụ:\n"
            "- `api healthy?`\n"
            "- `hôm nay ingest bao nhiêu doc?`\n"
            "- `pod nào đang lỗi?`"
        )
        await send_telegram_message(chat_id, welcome, reply_to_message_id=message_id)
        return

    logger.info("Telegram message from %s (chat %s): %.120s", user_id, chat_id, text)

    # Process and reply asynchronously
    asyncio.create_task(_process_and_reply_telegram(text, user_id, chat_id, message_id))


async def _process_and_reply_telegram(
    question: str, user_id: str, chat_id: int, message_id: int
) -> None:
    """Background task: call handler and post answer back to Telegram."""
    try:
        answer, needs_confirm, token = await handle_question(question, user_id)
        logger.info("Telegram answer for %s (needs_confirm=%s): %.200s", user_id, needs_confirm, answer)
        await send_telegram_message(chat_id, answer, reply_to_message_id=message_id)
    except Exception as exc:
        logger.error("Error processing Telegram question from %s: %s", user_id, exc, exc_info=True)


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive Telegram updates, verify secret token if configured, dispatch to background handler."""
    headers = request.headers
    telegram_secret_token = os.getenv("TELEGRAM_SECRET_TOKEN", "")
    if telegram_secret_token:
        secret = headers.get("x-telegram-bot-api-secret-token", "")
        if secret != telegram_secret_token:
            raise HTTPException(status_code=401, detail="Invalid Telegram secret token")

    body = await request.body()
    try:
        update = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    background_tasks.add_task(process_telegram_update, update)
    return {"ok": True}


async def run_telegram_polling() -> None:
    """Run long polling loop to fetch updates from Telegram."""
    logger.info("Starting Telegram long polling...")
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set — cannot run long polling")
        return

    offset = 0
    url = f"https://api.telegram.org/bot{telegram_bot_token}/getUpdates"
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                params = {"offset": offset, "timeout": 30}
                resp = await client.get(url, params=params, timeout=35.0)
                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        await process_telegram_update(update)
                else:
                    logger.error("Telegram getUpdates returned status %d: %s", resp.status_code, resp.text)
                    await asyncio.sleep(5)
            except asyncio.CancelledError:
                logger.info("Telegram long polling task cancelled")
                break
            except Exception as e:
                logger.error("Error in Telegram polling loop: %s", e)
                await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    global _telegram_polling_task
    # Only start polling if explicitly requested and token is present
    if os.getenv("TELEGRAM_POLLING", "false").lower() == "true":
        _telegram_polling_task = asyncio.create_task(run_telegram_polling())


@app.on_event("shutdown")
async def shutdown_event():
    global _telegram_polling_task
    if _telegram_polling_task:
        _telegram_polling_task.cancel()
        try:
            await _telegram_polling_task
        except asyncio.CancelledError:
            pass


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
