"""Multi-provider LLM client — DeepSeek (default), Gemini, Anthropic."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Awaitable, Callable

logger = logging.getLogger("chatops-bot.llm")

# Provider config: default model, OpenAI-compat base_url (None = native SDK), API key env var
_PROVIDERS: dict[str, dict[str, str | None]] = {
    "deepseek": {
        "default_model": "deepseek-v4-flash",
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
    "gemini": {
        "default_model": "gemini-3-flash-preview",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GEMINI_API_KEY",
    },
    "anthropic": {
        "default_model": "claude-sonnet-4-6",
        "base_url": None,
        "api_key_env": "ANTHROPIC_API_KEY",
    },
}

DEFAULT_PROVIDER = "deepseek"

ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


def _to_openai_tools(anthropic_tools: list[dict]) -> list[dict]:
    """Convert Anthropic tool schema format to OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        }
        for t in anthropic_tools
    ]


class LLMClient:
    """Unified async LLM client with tool-calling loop for DeepSeek, Gemini, and Anthropic."""

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.provider = (provider or os.getenv("CHATOPS_LLM_PROVIDER", DEFAULT_PROVIDER)).lower()
        if self.provider not in _PROVIDERS:
            raise ValueError(
                f"Unknown provider '{self.provider}'. Valid options: {list(_PROVIDERS)}"
            )
        cfg = _PROVIDERS[self.provider]
        self.model = model or os.getenv(
            f"{self.provider.upper()}_CHAT_MODEL",
            str(cfg["default_model"]),
        )
        self.api_key = api_key or os.getenv(str(cfg["api_key_env"]), "")
        self.base_url = cfg["base_url"]
        logger.info("LLMClient: provider=%s model=%s", self.provider, self.model)

    async def run_tool_loop(
        self,
        question: str,
        system: str,
        tool_executor: ToolExecutor,
        tool_definitions: list[dict],
        max_rounds: int = 5,
    ) -> str:
        """Run multi-turn tool-calling loop and return the final answer text."""
        if self.provider == "anthropic":
            return await self._loop_anthropic(question, system, tool_executor, tool_definitions, max_rounds)
        return await self._loop_openai_compat(question, system, tool_executor, tool_definitions, max_rounds)

    # ------------------------------------------------------------------
    # Anthropic native SDK loop
    # ------------------------------------------------------------------

    async def _loop_anthropic(
        self,
        question: str,
        system: str,
        tool_executor: ToolExecutor,
        tool_definitions: list[dict],
        max_rounds: int,
    ) -> str:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        messages: list[dict[str, Any]] = [{"role": "user", "content": question}]

        for _ in range(max_rounds):
            resp = await client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system,
                tools=tool_definitions,
                messages=messages,
            )
            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if not tool_uses:
                texts = [b.text for b in resp.content if hasattr(b, "text")]
                return "\n".join(texts) or "No answer generated."

            tool_results: list[dict[str, Any]] = []
            for tu in tool_uses:
                result = await tool_executor(tu.name, tu.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
            messages.append({"role": "assistant", "content": resp.content})
            messages.append({"role": "user", "content": tool_results})

        return "Unable to complete the query after multiple attempts."

    # ------------------------------------------------------------------
    # OpenAI-compatible loop (DeepSeek + Gemini)
    # ------------------------------------------------------------------

    async def _loop_openai_compat(
        self,
        question: str,
        system: str,
        tool_executor: ToolExecutor,
        tool_definitions: list[dict],
        max_rounds: int,
    ) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        oai_tools = _to_openai_tools(tool_definitions)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": question},
        ]

        for _ in range(max_rounds):
            resp = await client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                tools=oai_tools,
                messages=messages,
            )
            msg = resp.choices[0].message
            if not msg.tool_calls:
                return msg.content or "No answer generated."

            # Append assistant turn with tool_calls preserved for history
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            })

            # Execute each tool and append results
            for tc in msg.tool_calls:
                inputs = json.loads(tc.function.arguments or "{}")
                result = await tool_executor(tc.function.name, inputs)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        return "Unable to complete the query after multiple attempts."
