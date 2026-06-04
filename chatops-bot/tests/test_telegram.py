"""Tests for Telegram webhook and message processing."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app, verify_slack_signature


@pytest.fixture
def clean_telegram_env(monkeypatch):
    """Ensure environment is controlled for tests."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "mock-bot-token")
    monkeypatch.delenv("TELEGRAM_SECRET_TOKEN", raising=False)


def test_telegram_webhook_no_secret_success(clean_telegram_env):
    """If no secret token is configured, request passes without authentication."""
    with TestClient(app) as client:
        payload = {
            "update_id": 12345,
            "message": {
                "message_id": 1,
                "from": {"id": 98765, "username": "testuser"},
                "chat": {"id": 98765, "type": "private"},
                "text": "api healthy?"
            }
        }
        with patch("app.main.process_telegram_update", new_callable=AsyncMock) as mock_process:
            response = client.post("/telegram/webhook", json=payload)
            assert response.status_code == 200
            assert response.json() == {"ok": True}
            mock_process.assert_awaited_once_with(payload)


def test_telegram_webhook_with_secret_success(clean_telegram_env, monkeypatch):
    """If secret token is configured, request with valid header passes."""
    monkeypatch.setenv("TELEGRAM_SECRET_TOKEN", "my-secret-token")
    with TestClient(app) as client:
        payload = {
            "update_id": 12345,
            "message": {
                "message_id": 1,
                "from": {"id": 98765, "username": "testuser"},
                "chat": {"id": 98765, "type": "private"},
                "text": "api healthy?"
            }
        }
        with patch("app.main.process_telegram_update", new_callable=AsyncMock) as mock_process:
            headers = {"x-telegram-bot-api-secret-token": "my-secret-token"}
            response = client.post("/telegram/webhook", json=payload, headers=headers)
            assert response.status_code == 200
            assert response.json() == {"ok": True}
            mock_process.assert_awaited_once_with(payload)


def test_telegram_webhook_with_secret_invalid(clean_telegram_env, monkeypatch):
    """If secret token is configured, request with invalid header is rejected with 401."""
    monkeypatch.setenv("TELEGRAM_SECRET_TOKEN", "my-secret-token")
    with TestClient(app) as client:
        payload = {"update_id": 12345}
        headers = {"x-telegram-bot-api-secret-token": "wrong-secret-token"}
        response = client.post("/telegram/webhook", json=payload, headers=headers)
        assert response.status_code == 401
        assert "Invalid Telegram secret token" in response.text


def test_telegram_webhook_with_secret_missing(clean_telegram_env, monkeypatch):
    """If secret token is configured, request with missing header is rejected with 401."""
    monkeypatch.setenv("TELEGRAM_SECRET_TOKEN", "my-secret-token")
    with TestClient(app) as client:
        payload = {"update_id": 12345}
        response = client.post("/telegram/webhook", json=payload)
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_process_telegram_update_start_command(clean_telegram_env):
    """/start command triggers a welcome message reply."""
    from app.main import process_telegram_update

    update = {
        "update_id": 12345,
        "message": {
            "message_id": 42,
            "from": {"id": 98765, "username": "testuser"},
            "chat": {"id": 98765, "type": "private"},
            "text": "/start"
        }
    }
    with patch("app.main.send_telegram_message", new_callable=AsyncMock) as mock_send:
        await process_telegram_update(update)
        mock_send.assert_awaited_once()
        args, kwargs = mock_send.call_args
        assert args[0] == 98765
        assert "Xin chào!" in args[1]
        assert kwargs.get("reply_to_message_id") == 42


@pytest.mark.asyncio
async def test_process_telegram_update_query_workflow(clean_telegram_env):
    """A standard query processes the question and sends a reply."""
    from app.main import process_telegram_update

    update = {
        "update_id": 12345,
        "message": {
            "message_id": 101,
            "from": {"id": 98765, "username": "testuser"},
            "chat": {"id": 98765, "type": "private"},
            "text": "api healthy?"
        }
    }
    
    with patch("app.main.handle_question", new_callable=AsyncMock, return_value=("Everything is OK", False, None)) as mock_handle, \
         patch("app.main.send_telegram_message", new_callable=AsyncMock) as mock_send:
        # Wait briefly for background task creation
        await process_telegram_update(update)
        # Give event loop a tiny slice to run the background task
        import asyncio
        await asyncio.sleep(0.01)

        mock_handle.assert_awaited_once_with("api healthy?", "testuser")
        mock_send.assert_awaited_once_with(98765, "Everything is OK", reply_to_message_id=101)


@pytest.mark.asyncio
async def test_send_telegram_message_fallback_on_parse_error(clean_telegram_env, httpx_mock):
    """If Telegram rejects Markdown parse, it falls back to plain text."""
    from app.main import send_telegram_message

    # Setup the first call to fail with 400 Bad Request
    httpx_mock.add_response(
        method="POST",
        url="https://api.telegram.org/botmock-bot-token/sendMessage",
        status_code=400,
        text="Bad Request: can't parse entities"
    )

    # Setup the second fallback call to succeed
    httpx_mock.add_response(
        method="POST",
        url="https://api.telegram.org/botmock-bot-token/sendMessage",
        status_code=200,
        json={"ok": True}
    )

    await send_telegram_message(98765, "Some *bad_markdown", reply_to_message_id=12)

    # Verify requests sent
    requests = httpx_mock.get_requests()
    assert len(requests) == 2

    # Verify first call used Markdown
    import json
    first_call_json = json.loads(requests[0].read())
    assert first_call_json["parse_mode"] == "Markdown"

    # Verify second call dropped parse_mode (fallback to plain text)
    second_call_json = json.loads(requests[1].read())
    assert "parse_mode" not in second_call_json
