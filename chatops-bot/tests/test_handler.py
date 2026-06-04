"""Tests for question handler — permission tiers and LLM tool-calling loop."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm import LLMClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_llm_client(answer: str = "All good ✅") -> MagicMock:
    """Return a LLMClient mock whose run_tool_loop resolves to `answer`."""
    mock = MagicMock(spec=LLMClient)
    mock.run_tool_loop = AsyncMock(return_value=answer)
    return mock


# ---------------------------------------------------------------------------
# Permission tier tests (no LLM call needed)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_destructive_intent_denied(isolated_audit_log):
    from app.handler import handle_question
    answer, needs_confirm, token = await handle_question("Delete pod api-0", "U123")
    assert "⛔" in answer or "not permitted" in answer.lower()
    assert needs_confirm is False
    assert token is None
    assert isolated_audit_log.exists()


@pytest.mark.asyncio
async def test_write_intent_requires_confirmation(isolated_audit_log):
    from app.handler import handle_question
    answer, needs_confirm, token = await handle_question("Scale api to 5 replicas", "U123")
    assert needs_confirm is True
    assert token is not None and len(token) > 0
    assert "confirm" in answer.lower()


# ---------------------------------------------------------------------------
# READ tier — LLM tool-calling loop tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_read_intent_calls_llm_with_tools(isolated_audit_log):
    """READ questions go through the LLM tool-calling loop."""
    mock_client = _make_mock_llm_client("InsightHub is *healthy* ✅ — API returned HTTP 200.")

    with patch("app.handler.check_api_health", new_callable=AsyncMock,
               return_value={"status": "ok", "http_code": 200}):
        from app.handler import handle_question
        answer, needs_confirm, token = await handle_question(
            "InsightHub có healthy không?", "U123", llm_client=mock_client
        )

    assert "healthy" in answer.lower() or "ok" in answer.lower()
    assert needs_confirm is False
    assert token is None
    mock_client.run_tool_loop.assert_awaited_once()


@pytest.mark.asyncio
async def test_failing_pods_question(isolated_audit_log):
    """'Pod nào đang lỗi?' routes through LLM loop."""
    mock_client = _make_mock_llm_client("No pods are currently failing ✅")

    with patch("app.handler.get_failing_pods",
               return_value={"failing": [], "failing_count": 0, "total_pods": 5}):
        from app.handler import handle_question
        answer, _, _ = await handle_question(
            "Pod nào đang lỗi?", "U456", llm_client=mock_client
        )

    assert answer  # any non-empty reply
    mock_client.run_tool_loop.assert_awaited_once()


@pytest.mark.asyncio
async def test_unknown_tool_handled_gracefully(isolated_audit_log):
    """Unknown tool names don't crash _execute_tool."""
    from app.handler import _execute_tool
    result = await _execute_tool("nonexistent_tool", {}, "U123")
    assert "error" in result or "Unknown tool" in str(result)


# ---------------------------------------------------------------------------
# LLMClient — tool_executor integration (audit log written)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tool_executor_writes_audit(isolated_audit_log):
    """tool_executor inside handle_question writes audit records."""
    # Simulate LLM calling check_api_health via tool_executor
    async def fake_loop(question, system, tool_executor, tool_definitions, max_rounds=5):
        result = await tool_executor("check_api_health", {})
        return f"status={result.get('status')}"

    mock_client = MagicMock(spec=LLMClient)
    mock_client.run_tool_loop = AsyncMock(side_effect=fake_loop)

    with patch("app.handler.check_api_health", new_callable=AsyncMock,
               return_value={"status": "ok", "http_code": 200}):
        from app.handler import handle_question
        answer, _, _ = await handle_question(
            "health check?", "U789", llm_client=mock_client
        )

    assert "ok" in answer
    lines = isolated_audit_log.read_text().strip().splitlines()
    tools_logged = [json.loads(l)["tool"] for l in lines]
    assert "check_api_health" in tools_logged


# ---------------------------------------------------------------------------
# LLMClient unit tests
# ---------------------------------------------------------------------------

class TestLLMClientInit:
    def test_deepseek_is_default(self, monkeypatch):
        monkeypatch.delenv("CHATOPS_LLM_PROVIDER", raising=False)
        client = LLMClient()
        assert client.provider == "deepseek"
        assert client.model == "deepseek-v4-flash"

    def test_gemini_provider(self, monkeypatch):
        monkeypatch.setenv("CHATOPS_LLM_PROVIDER", "gemini")
        client = LLMClient()
        assert client.provider == "gemini"
        assert client.model == "gemini-3-flash-preview"

    def test_anthropic_provider(self, monkeypatch):
        monkeypatch.setenv("CHATOPS_LLM_PROVIDER", "anthropic")
        client = LLMClient()
        assert client.provider == "anthropic"
        assert client.model == "claude-sonnet-4-6"

    def test_explicit_provider_overrides_env(self, monkeypatch):
        monkeypatch.setenv("CHATOPS_LLM_PROVIDER", "anthropic")
        client = LLMClient(provider="gemini")
        assert client.provider == "gemini"

    def test_explicit_model_overrides_default(self):
        client = LLMClient(provider="deepseek", model="deepseek-chat")
        assert client.model == "deepseek-chat"

    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMClient(provider="unknownprovider")

    def test_model_env_var_override(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_CHAT_MODEL", "deepseek-reasoner")
        client = LLMClient(provider="deepseek")
        assert client.model == "deepseek-reasoner"
