"""Multi-provider tool-calling handler — answers operational questions about InsightHub."""
import logging
from pathlib import Path
from typing import Any

from app.audit import log_tool_call
from app.llm import LLMClient
from app.permissions import PermissionTier, classify_intent, issue_confirmation_token
from app.tools import TOOL_DEFINITIONS, check_api_health, get_failing_pods, get_ingest_count_today, K8S_NAMESPACE

logger = logging.getLogger("chatops-bot.handler")

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system.md"


def _load_system_prompt() -> str:
    try:
        return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return (
            "You are InsightHub ops bot. Answer infra questions concisely using tools. "
            "Always cite specific data (counts, statuses, timestamps). "
            "If a tool returns an error, report it honestly."
        )


async def handle_question(
    question: str,
    user_id: str,
    llm_client: LLMClient | None = None,
    http_client: Any = None,
) -> tuple[str, bool, str | None]:
    """
    Handle one operational question from Slack.

    Returns:
        (answer_text, needs_confirmation, confirmation_token_or_None)
    """
    tier = classify_intent(question)

    if tier == PermissionTier.DESTRUCTIVE:
        log_tool_call(
            user_id, "permission_check",
            {"question": question, "tier": "destructive"},
            "denied — destructive action blocked",
            approved=False,
        )
        return (
            "⛔ Destructive actions are not permitted via the bot. "
            "Use the runbook and obtain approval via the standard change process.",
            False, None,
        )

    if tier == PermissionTier.WRITE:
        token = issue_confirmation_token(user_id)
        log_tool_call(
            user_id, "permission_check",
            {"question": question, "tier": "write"},
            "confirmation required",
        )
        return (
            f"⚠️ This action requires confirmation.\n"
            f"Reply with: `confirm {token}` within 60 seconds to proceed.",
            True, token,
        )

    # READ tier — run multi-turn tool-calling loop via configured LLM provider
    client = llm_client or LLMClient()
    system = _load_system_prompt()

    async def tool_executor(name: str, inputs: dict[str, Any]) -> dict[str, Any]:
        return await _execute_tool(name, inputs, user_id, http_client)

    answer = await client.run_tool_loop(
        question=question,
        system=system,
        tool_executor=tool_executor,
        tool_definitions=TOOL_DEFINITIONS,
    )
    return answer, False, None


async def _execute_tool(
    name: str,
    inputs: dict[str, Any],
    user_id: str,
    http_client: Any = None,
) -> dict[str, Any]:
    """Execute a single tool call and write audit record."""
    try:
        if name == "check_api_health":
            result = await check_api_health(http_client)
        elif name == "get_ingest_count_today":
            result = await get_ingest_count_today(http_client)
        elif name == "get_failing_pods":
            ns = inputs.get("namespace", K8S_NAMESPACE)
            result = get_failing_pods(ns)
        else:
            result = {"error": f"Unknown tool: {name}"}
        log_tool_call(user_id, name, inputs, str(result)[:300])
        return result
    except Exception as exc:
        log_tool_call(user_id, name, inputs, f"error: {exc}", approved=False)
        return {"error": str(exc)}
