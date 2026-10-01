import asyncio
from dataclasses import replace
from unittest.mock import patch

import httpx
import pytest
from app.config import Settings
from app.model import ModelSummaryError, summarize


@pytest.mark.parametrize(
    "status,body,code",
    [
        (429, "budget exceeded", "budget_exceeded"),
        (422, "policy_blocked", "policy_blocked"),
        (503, "private provider detail", "model_unavailable"),
    ],
)
def test_summary_failures_classified_without_body(status, body, code):
    settings = replace(
        Settings.from_env(),
        model_key="virtual-test",
        model_name="bot-chat",
        model_url="http://gateway.local/v1",
    )
    response = httpx.Response(
        status,
        text=body,
        request=httpx.Request("POST", "http://gateway.local/v1/chat/completions"),
    )
    with patch("app.model.httpx.AsyncClient") as client:
        client.return_value.__aenter__.return_value.post.return_value = response
        with pytest.raises(ModelSummaryError) as err:
            asyncio.run(summarize("ready=1", settings))
    assert err.value.code == code
    assert "private" not in str(err.value)
