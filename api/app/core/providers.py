"""Small REST adapters share bounded timeouts and sanitized transport errors."""

import logging
import uuid
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import (
    BudgetExceeded,
    GuardrailUnavailable,
    PolicyBlocked,
    ProviderError,
)
from app.core.request_context import request_id

logger = logging.getLogger("insighthub.providers")


def post_json(
    url: str, *, headers: dict[str, str], payload: dict[str, Any]
) -> dict[str, Any]:
    try:
        if get_settings().litellm_api_key:
            correlation = request_id.get() or str(uuid.uuid4())
            headers = {**headers, "X-Client-Request-Id": correlation}
            payload = {**payload, "metadata": {"day6_parent_request_id": correlation}}
        # Do not inherit proxies, follow redirects, or log response bodies/URLs.
        with httpx.Client(
            timeout=get_settings().provider_timeout_seconds,
            trust_env=False,
            follow_redirects=False,
        ) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Invalid JSON object")
            return data
    except httpx.HTTPStatusError as exc:
        logger.warning("AI provider request failed")
        if get_settings().litellm_api_key:
            # Inspect only the machine error classification; never log its body.
            try:
                error = exc.response.json().get("error", {})
                code = str(error.get("code", "")) + " " + str(error.get("type", ""))
                message = str(error.get("message", ""))
            except (ValueError, AttributeError, TypeError):
                code = message = ""
            if "budget" in (code + message).lower():
                raise BudgetExceeded() from None
            if "policy_blocked" in code + message:
                raise PolicyBlocked() from None
            if "guardrail_unavailable" in code + message:
                raise GuardrailUnavailable() from None
        raise ProviderError(
            retryable=exc.response.status_code == 429 or exc.response.status_code >= 500
        ) from None
    except (httpx.TimeoutException, httpx.NetworkError):
        logger.warning("AI provider request failed")
        raise ProviderError(retryable=True) from None
    except (httpx.HTTPError, ValueError):
        logger.warning("AI provider request failed")
        raise ProviderError() from None


def token_count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def indexed_embeddings(data: dict[str, Any], count: int) -> list[Any]:
    items = data["data"]
    if len(items) != count or any(type(item.get("index")) is not int for item in items):
        raise ProviderError()
    if sorted(item["index"] for item in items) != list(range(count)):
        raise ProviderError()
    return [item["embedding"] for item in sorted(items, key=lambda item: item["index"])]
