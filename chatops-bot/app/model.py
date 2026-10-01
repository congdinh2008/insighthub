"""Optional bounded LLM commentary over already sanitized operational facts."""

from pathlib import Path

import httpx

from .config import Settings


class ModelSummaryError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


SYSTEM_PROMPT = (
    Path(__file__).resolve().parents[1] / "prompts" / "system.txt"
).read_text()


async def summarize(facts: str, settings: Settings) -> str | None:
    if not (settings.model_url and settings.model_name and settings.model_key):
        return None
    payload = {
        "model": settings.model_name,
        "temperature": 0,
        "max_tokens": 120,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": facts[:3000]},
        ],
    }
    try:
        async with httpx.AsyncClient(
            timeout=25, trust_env=False, follow_redirects=False
        ) as client:
            response = await client.post(
                settings.model_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + settings.model_key},
                json=payload,
            )
            if response.is_error:
                code = "model_unavailable"
                if (
                    response.status_code in (400, 402, 429)
                    and "budget" in response.text.lower()
                ):
                    code = "budget_exceeded"
                elif response.status_code == 422:
                    code = "policy_blocked"
                raise ModelSummaryError(code)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if isinstance(content, str) and 0 < len(content) <= 1000:
                return content
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        raise ModelSummaryError("model_unavailable") from None
    raise ModelSummaryError("invalid_model_output")
