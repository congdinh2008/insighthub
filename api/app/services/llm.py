"""
InsightHub API — LLM service (RAG generation)

Provider: gemini (default) | anthropic | bedrock | ollama
Đổi provider qua env LLM_PROVIDER, không sửa code.

Khi không có API key (gemini/anthropic) → fallback extractive answer
để lab vẫn chạy được end-to-end (chất lượng kém nhưng pipeline ok).
"""
import logging
import time

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger("insighthub.llm")
settings = get_settings()

SYSTEM_PROMPT = """Bạn là trợ lý của InsightHub. Trả lời câu hỏi của người dùng \
CHỈ dựa trên các đoạn tài liệu được cung cấp trong <context>. \
Nếu context không chứa thông tin để trả lời, hãy nói rõ là không tìm thấy. \
Luôn trích dẫn nguồn theo định dạng [nguồn: tên_file]."""


def _build_user_message(question: str, contexts: list[dict]) -> str:
    blocks = []
    for c in contexts:
        blocks.append(
            f"<doc source=\"{c['source']}\">\n{c['chunk_text']}\n</doc>"
        )
    context_str = "\n\n".join(blocks) if blocks else "(không có tài liệu nào)"
    return f"<context>\n{context_str}\n</context>\n\nCâu hỏi: {question}"


def _fallback_extractive(question: str, contexts: list[dict]) -> dict:
    """Khi không có API key, trả về snippet đầu tiên — pipeline vẫn chạy."""
    snippet = contexts[0]["chunk_text"][:300] if contexts else "(không có dữ liệu)"
    return {
        "answer": f"[Chế độ fallback — không có LLM key / Ollama không sẵn sàng]\n\n{snippet}...",
        "sources": list({c["source"] for c in contexts}),
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


# ============================================================
# Gemini provider (default)
# ============================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _gemini_generate(question: str, contexts: list[dict]) -> dict:
    """
    Gọi Google Gemini API.
    Ref: https://ai.google.dev/gemini-api/docs/text-generation
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    model_name = settings.resolved_chat_model

    user_msg = _build_user_message(question, contexts)

    resp = client.models.generate_content(
        model=model_name,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=settings.llm_max_tokens,
        ),
    )

    # Gemini usage_metadata: prompt_token_count + candidates_token_count
    usage = resp.usage_metadata if hasattr(resp, "usage_metadata") else None
    return {
        "answer": resp.text or "",
        "sources": list({c["source"] for c in contexts}),
        "usage": {
            "input_tokens": getattr(usage, "prompt_token_count", 0) if usage else 0,
            "output_tokens": getattr(usage, "candidates_token_count", 0) if usage else 0,
        },
    }


# ============================================================
# Anthropic provider
# ============================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _anthropic_generate(question: str, contexts: list[dict]) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    model_name = settings.resolved_chat_model
    # Anthropic prompt caching: đánh dấu system prompt là cache_control ephemeral
    # → input token của system prompt được cache, giảm chi phí khi lặp context.
    resp = client.messages.create(
        model=model_name,
        max_tokens=settings.llm_max_tokens,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": _build_user_message(question, contexts)}],
    )
    answer = "".join(block.text for block in resp.content if block.type == "text")
    return {
        "answer": answer,
        "sources": list({c["source"] for c in contexts}),
        "usage": {
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
        },
    }


# ============================================================
# Ollama provider (local — không cần API key)
# ============================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _ollama_generate(question: str, contexts: list[dict]) -> dict:
    """
    Gọi Ollama local. Model phải đã pull: ollama pull deepseek-r1:14b.
    Ref: https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion
    """
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    model_name = settings.resolved_chat_model

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(question, contexts)},
        ],
        "stream": False,
        "options": {"num_predict": settings.llm_max_tokens},
    }

    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    answer = data.get("message", {}).get("content", "")
    return {
        "answer": answer,
        "sources": list({c["source"] for c in contexts}),
        "usage": {
            # Ollama không trả token chi tiết như API thương mại,
            # nhưng có eval_count + prompt_eval_count
            "input_tokens": data.get("prompt_eval_count", 0),
            "output_tokens": data.get("eval_count", 0),
        },
    }


# ============================================================
# LiteLLM gateway provider (Day 6 — FinOps)
# ============================================================
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _litellm_generate(question: str, contexts: list[dict]) -> dict:
    """
    Route qua LiteLLM proxy (OpenAI-compatible) — MH9.
    Dùng LITELLM_BASE_URL + LITELLM_API_KEY (virtual key có budget cap).
    """
    url = f"{settings.litellm_base_url.rstrip('/')}/v1/chat/completions"
    payload = {
        "model": settings.resolved_chat_model,
        "max_tokens": settings.llm_max_tokens,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(question, contexts)},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.litellm_api_key}"}
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    answer = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {
        "answer": answer,
        "sources": list({c["source"] for c in contexts}),
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
    }


# ============================================================
# Dispatcher
# ============================================================
def generate(question: str, contexts: list[dict]) -> dict:
    """
    Sinh câu trả lời RAG. Trả về dict: {answer, sources, usage}.
    Tự fallback extractive khi provider không khả dụng (không key / Ollama down).
    """
    # Day 4 chaos hook — chỉ active khi LLM_CHAOS_LATENCY_MS > 0 (mặc định 0 = tắt).
    # Delay nằm trong window llm_call_latency.observe() ở chat.py ⇒ đẩy metric
    # insighthub_llm_call_latency_seconds lên cao → trip InsightHubLLMLatencyAnomaly.
    if settings.llm_chaos_latency_ms > 0:
        logger.warning(
            "CHAOS: inject %dms latency vào LLM call (LLM_CHAOS_LATENCY_MS đang bật)",
            settings.llm_chaos_latency_ms,
        )
        time.sleep(settings.llm_chaos_latency_ms / 1000.0)

    provider = settings.llm_provider.lower()

    try:
        if provider == "litellm":
            if not (settings.litellm_base_url and settings.litellm_api_key):
                logger.warning("LLM_PROVIDER=litellm nhưng LITELLM_BASE_URL/LITELLM_API_KEY trống — fallback extractive")
                return _fallback_extractive(question, contexts)
            return _litellm_generate(question, contexts)

        if provider == "gemini":
            if not settings.gemini_api_key:
                logger.warning("LLM_PROVIDER=gemini nhưng GEMINI_API_KEY trống — fallback extractive")
                return _fallback_extractive(question, contexts)
            return _gemini_generate(question, contexts)

        if provider in ("anthropic", "bedrock"):
            if not settings.anthropic_api_key:
                logger.warning("LLM_PROVIDER=anthropic nhưng ANTHROPIC_API_KEY trống — fallback extractive")
                return _fallback_extractive(question, contexts)
            return _anthropic_generate(question, contexts)

        if provider == "ollama":
            try:
                return _ollama_generate(question, contexts)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Ollama call failed (%s) — fallback extractive", exc)
                return _fallback_extractive(question, contexts)

        logger.warning("Unsupported LLM_PROVIDER='%s' — fallback extractive", provider)
        return _fallback_extractive(question, contexts)

    except Exception as exc:  # noqa: BLE001
        logger.error("LLM generation failed (%s): %s — fallback extractive", provider, exc)
        return _fallback_extractive(question, contexts)
