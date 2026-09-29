"""Mandatory policy boundary tests, independent of external model behavior."""

import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("day6_hooks", ROOT / "gateway/hooks.py")
hooks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hooks)


def invoke(data, alias="day6-insighthub", kind="completion"):
    return asyncio.run(
        hooks.policy.async_pre_call_hook(
            SimpleNamespace(key_alias=alias), None, data, kind
        )
    )


@pytest.fixture(autouse=True)
def audit(tmp_path, monkeypatch):
    monkeypatch.setenv("DAY6_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("DAY6_POLICY_MODE", "enforce")
    monkeypatch.setattr(hooks, "require_accounting", AsyncMock())


def test_spoofed_identity_overwritten_and_guards_cannot_be_disabled():
    data = {
        "model": "app-chat",
        "messages": [{"role": "user", "content": "safe"}],
        "metadata": {"day6_workload": "guardrail"},
        "guardrails": [],
        "max_tokens": 9000,
    }
    with patch.object(hooks, "check_text", new=AsyncMock()) as guard:
        out = invoke(data)
    assert out["metadata"]["day6_workload"] == "insighthub"
    assert out["max_tokens"] == 1024
    guard.assert_awaited_once()


@pytest.mark.parametrize(
    "extra",
    [{"stream": True}, {"tools": [{}]}, {"functions": [{}]}, {"max_tokens": -1}],
)
def test_unsupported_generation_rejected(extra):
    with pytest.raises(HTTPException):
        invoke({"messages": [{"role": "user", "content": "hello"}], **extra})


def test_master_key_not_workload():
    with pytest.raises(HTTPException) as err:
        invoke({}, alias=None)
    assert err.value.status_code == 403


@pytest.mark.parametrize("count", [2, 0, -1, True, "1"])
def test_extra_choices_rejected_before_provider_admission(count):
    with patch.object(hooks, "check_text", AsyncMock()) as guard:
        with pytest.raises(HTTPException) as err:
            invoke({"messages": [{"role": "user", "content": "safe"}], "n": count})
        assert err.value.status_code == 400
        assert err.value.detail == {"code": "single_completion_required"}
        guard.assert_not_awaited()


@pytest.mark.parametrize("choices", [None, [], ["first", "unreviewed second"]])
def test_unexpected_provider_choice_count_never_released(choices):
    with pytest.raises(HTTPException) as err:
        asyncio.run(
            hooks.policy.async_post_call_success_hook(
                {"messages": [{"role": "user", "content": "safe"}]},
                SimpleNamespace(key_alias="day6-insighthub"),
                SimpleNamespace(choices=choices),
            )
        )
    assert err.value.status_code == 502


def test_single_completion_is_checked_and_returned():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="safe"))]
    )
    with patch.object(hooks, "check_text", AsyncMock()) as guard:
        result = asyncio.run(
            hooks.policy.async_post_call_success_hook(
                {"messages": [{"role": "user", "content": "safe"}]},
                SimpleNamespace(key_alias="day6-insighthub"),
                response,
            )
        )
    assert result is response
    guard.assert_awaited_once_with("safe", "output")


def test_embedding_preserves_operation_contract():
    out = invoke(
        {"model": "app-embedding", "input": ["data"], "dimensions": 1024},
        kind="embedding",
    )
    assert "max_tokens" not in out
    assert out["dimensions"] == 1024


def test_unavailable_guard_aborts_provider_admission():
    with (
        patch.object(
            hooks, "check_text", new=AsyncMock(side_effect=HTTPException(503))
        ),
        pytest.raises(HTTPException),
    ):
        invoke({"messages": [{"role": "user", "content": "safe"}]})


def test_accounting_outage_blocks_even_cached_valid_key():
    with (
        patch.object(
            hooks, "require_accounting", AsyncMock(side_effect=HTTPException(503))
        ),
        patch.object(hooks, "check_text", AsyncMock()) as guard,
    ):
        with pytest.raises(HTTPException) as err:
            invoke({"messages": [{"role": "user", "content": "safe"}]})
        assert err.value.status_code == 503
        guard.assert_not_awaited()
