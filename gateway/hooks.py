"""Mandatory gateway policy and sanitized ledger for all Day 06 workload keys."""

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
import psycopg
from fastapi import HTTPException
from litellm.integrations.custom_logger import CustomLogger

WORKLOADS = {
    "day6-insighthub": "insighthub",
    "day6-bot": "chatops-bot",
    "day6-coding": "coding-workflow",
    "day6-guard": "guardrail",
    "day6-evaluator": "evaluator",
}


def record(row: dict[str, Any]) -> None:
    path = Path(os.environ.get("DAY6_AUDIT_PATH", "/tmp/day6-gateway-audit.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (
        json.dumps({"timestamp": time.time(), **row}, ensure_ascii=False) + "\n"
    ).encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)


async def check_text(text: str, phase: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=18, trust_env=False) as client:
            response = await client.post(
                os.environ["GUARD_URL"].rstrip("/") + "/check",
                headers={"X-Guard-Key": os.environ["GUARD_API_KEY"]},
                json={"text": text, "phase": phase},
            )
            response.raise_for_status()
            result = response.json()
        if type(result.get("allowed")) is not bool:
            raise ValueError("Invalid guard response")
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        raise HTTPException(503, detail={"code": "guardrail_unavailable"}) from None
    if not result["allowed"]:
        raise HTTPException(422, detail={"code": "policy_blocked"})


async def require_accounting() -> None:
    """A cached key must not admit inference while its accounting DB is unavailable."""
    try:
        async with await psycopg.AsyncConnection.connect(
            os.environ["DAY6_ACCOUNTING_URL"],
            connect_timeout=3,
            autocommit=True,
            options="-c statement_timeout=2000",
        ) as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    'SELECT COALESCE(SUM(spend), 0) FROM "LiteLLM_VerificationToken" WHERE key_alias = ANY(%s)',
                    (list(WORKLOADS),),
                )
                row = await cursor.fetchone()
                if row is None:
                    raise ValueError("accounting unavailable")
                spend = float(row[0])
    except (psycopg.Error, KeyError, ValueError, TypeError):
        raise HTTPException(503, detail={"code": "accounting_unavailable"}) from None
    # Keep 20% of the five-dollar acceptance envelope available for recovery.
    if spend >= 4.0:
        raise HTTPException(429, detail={"code": "lab_budget_exceeded"})


class Day6Policy(CustomLogger):
    enforces_request_content = True

    async def async_pre_call_hook(self, user_api_key_dict, cache, data, call_type):
        alias = getattr(user_api_key_dict, "key_alias", None)
        if call_type not in {"completion", "acompletion", "embedding", "aembedding"}:
            raise HTTPException(403, detail={"code": "operation_not_enabled"})
        if alias not in WORKLOADS:
            raise HTTPException(403, detail={"code": "workload_identity_required"})
        await require_accounting()
        if data.get("stream"):
            raise HTTPException(400, detail={"code": "streaming_not_enabled"})
        if data.get("tools") or data.get("tool_choice") or data.get("functions"):
            raise HTTPException(403, detail={"code": "tools_not_enabled"})
        # Authenticated identity owns these fields, never incoming client metadata.
        meta = data.setdefault("metadata", {})
        meta["day6_workload"] = WORKLOADS[alias]
        meta["day6_request_id"] = str(uuid.uuid4())
        meta["day6_run_id"] = os.environ.get("DAY6_RUN_ID", "local")
        if call_type not in {"embedding", "aembedding"}:
            # All Day06 consumers use one answer. Additional choices would widen
            # both the output review boundary and the per-request token budget.
            if type(data.get("n", 1)) is not int or data.get("n", 1) != 1:
                raise HTTPException(400, detail={"code": "single_completion_required"})
            data["n"] = 1
            cap = data.get("max_tokens", data.get("max_completion_tokens", 512))
            if type(cap) is not int or cap < 1:
                raise HTTPException(400, detail={"code": "invalid_token_limit"})
            data["max_tokens"] = min(cap, 1024)
            data.pop("max_completion_tokens", None)
        # Guard/evaluator keys are distributed only to trusted local services.
        # They have restricted model aliases and no application/executor credentials.
        if alias not in {"day6-guard", "day6-evaluator"} and call_type not in {
            "embedding",
            "aembedding",
        }:
            messages = data.get("messages")
            if not isinstance(messages, list) or not messages:
                raise HTTPException(400, detail={"code": "invalid_messages"})
            if not all(
                isinstance(m, dict) and m.get("role") in {"system", "user", "assistant"}
                for m in messages
            ):
                raise HTTPException(400, detail={"code": "invalid_messages"})
            texts = [m.get("content", "") for m in messages]
            if not all(isinstance(t, str) for t in texts):
                raise HTTPException(400, detail={"code": "text_only"})
            text = "\n".join(texts)
            if not text or len(text) > 24000:
                raise HTTPException(413, detail={"code": "input_too_large"})
            if os.environ.get("DAY6_POLICY_MODE", "enforce") == "enforce":
                try:
                    await check_text(text, "input")
                except HTTPException as exc:
                    record(
                        {
                            "event": "denied",
                            "request_id": meta["day6_request_id"],
                            "workload": WORKLOADS[alias],
                            "reason": exc.detail,
                        }
                    )
                    raise
        record(
            {
                "event": "admitted",
                "request_id": meta["day6_request_id"],
                "workload": WORKLOADS[alias],
                "model_alias": data.get("model"),
                "operation": call_type,
                "policy_mode": os.environ.get("DAY6_POLICY_MODE", "enforce"),
            }
        )
        return data

    async def async_post_call_success_hook(self, data, user_api_key_dict, response):
        alias = getattr(user_api_key_dict, "key_alias", None)
        if (
            alias in {"day6-insighthub", "day6-bot", "day6-coding"}
            and os.environ.get("DAY6_POLICY_MODE", "enforce") == "enforce"
        ):
            choices = getattr(response, "choices", None)
            if choices is not None or data.get("messages"):
                if not isinstance(choices, list) or len(choices) != 1:
                    raise HTTPException(502, detail={"code": "invalid_model_output"})
            if choices:
                content = getattr(choices[0].message, "content", None)
                if not isinstance(content, str) or not content:
                    raise HTTPException(502, detail={"code": "invalid_model_output"})
                try:
                    await check_text(content, "output")
                except HTTPException as exc:
                    record(
                        {
                            "event": "denied",
                            "phase": "output",
                            "workload": WORKLOADS[alias],
                            "request_id": (data.get("metadata") or {}).get(
                                "day6_request_id"
                            ),
                            "reason": exc.detail,
                        }
                    )
                    raise
        return response

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        params = kwargs.get("litellm_params", {})
        meta = params.get("metadata") or kwargs.get("metadata") or {}
        usage = getattr(response_obj, "usage", None)
        usage = usage.model_dump() if hasattr(usage, "model_dump") else usage or {}
        record(
            {
                "event": "completion",
                "request_id": meta.get("day6_request_id"),
                "provider_request_id": getattr(response_obj, "id", None),
                "run_id": meta.get("day6_run_id"),
                "parent_request_id": meta.get("day6_parent_request_id"),
                "workload": meta.get("day6_workload"),
                "model": kwargs.get("model"),
                "provider": params.get("custom_llm_provider"),
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens", 0),
                "cached_tokens": (usage.get("prompt_tokens_details") or {}).get(
                    "cached_tokens", 0
                ),
                "cost_usd": kwargs.get("response_cost"),
                "duration_seconds": (end_time - start_time).total_seconds(),
            }
        )

    async def async_post_call_failure_hook(
        self, request_data, original_exception, user_api_key_dict, traceback_str=None
    ):
        alias = getattr(user_api_key_dict, "key_alias", None)
        reason = (
            "budget_denied"
            if "budget" in type(original_exception).__name__.lower()
            else "request_failed"
        )
        record(
            {
                "event": reason,
                "workload": WORKLOADS.get(alias, "unauthenticated"),
                "request_id": (request_data.get("metadata") or {}).get(
                    "day6_request_id"
                ),
            }
        )
        return None

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        meta = kwargs.get("litellm_params", {}).get("metadata") or {}
        record(
            {
                "event": "upstream_failure",
                "request_id": meta.get("day6_request_id"),
                "workload": meta.get("day6_workload"),
                "cost_usd": None,
            }
        )


policy = Day6Policy(turn_off_message_logging=True)
