"""NeMo's fail-closed error envelope must not become a policy PASS in evaluation."""

import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "guard_service", ROOT / "security/guardrails/service.py"
)
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


@pytest.mark.parametrize(
    "status,content",
    [("blocked", service.INTERNAL_ERROR_MESSAGE), ("modified", "redacted")],
)
def test_rail_failure_is_unavailable_not_policy_denial(monkeypatch, status, content):
    monkeypatch.setenv("GUARD_API_KEY", "test-guard")
    monkeypatch.setattr(
        service,
        "rails",
        SimpleNamespace(
            check_async=AsyncMock(
                return_value=SimpleNamespace(
                    status=SimpleNamespace(value=status),
                    content=content,
                    rail="self check input",
                )
            )
        ),
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            service.check(
                service.CheckRequest(text="ordinary question", phase="input"),
                "test-guard",
            )
        )
    assert error.value.status_code == 503
