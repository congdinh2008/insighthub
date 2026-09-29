"""Day 06 guardrail boundary; never return unchecked RAG contexts to a client."""

from typing import Any, Literal

import httpx

from app.core.config import get_settings
from app.core.errors import GuardrailUnavailable, PolicyBlocked
from app.core.request_context import request_id


def check(text: str, phase: Literal["input", "context", "output"]) -> None:
    settings = get_settings()
    if not settings.security_enabled:
        return
    try:
        with httpx.Client(
            timeout=20, trust_env=False, follow_redirects=False
        ) as client:
            response = client.post(
                settings.guardrail_url.rstrip("/") + "/check",
                headers={
                    "X-Guard-Key": settings.guardrail_api_key,
                    "X-Request-ID": request_id.get(),
                },
                json={"text": text, "phase": phase},
            )
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict) or type(data.get("allowed")) is not bool:
            raise GuardrailUnavailable()
        if not data["allowed"]:
            raise PolicyBlocked()
    except (httpx.HTTPError, ValueError, TypeError):
        raise GuardrailUnavailable() from None


def safe_contexts(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove unsafe chunks from both generation and the HTTP response."""
    result = []
    for context in contexts:
        try:
            check(str(context["chunk_text"]), "context")
        except PolicyBlocked:
            continue
        result.append(context)
    if contexts and not result:
        raise PolicyBlocked()
    return result
