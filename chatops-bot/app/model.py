"""Optional bounded LLM commentary over already sanitized operational facts."""

from pathlib import Path

import httpx

from .config import Settings

SYSTEM_PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "system.txt").read_text()


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
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(settings.model_url.rstrip("/") + "/chat/completions",
                                         headers={"Authorization": "Bearer " + settings.model_key},
                                         json=payload)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if isinstance(content, str) and 0 < len(content) <= 1000:
                return content
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        pass
    return None
