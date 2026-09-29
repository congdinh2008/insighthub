from unittest.mock import patch

import httpx
import pytest
from app.core.config import Settings
from app.core.errors import GuardrailUnavailable, PolicyBlocked
from app.main import app
from app.services.guardrails import check, safe_contexts
from fastapi.testclient import TestClient
from support import real_config


def config(**extra):
    return real_config(
        openai_api_key="",
        litellm_api_key="workload-test",
        security_enabled=True,
        guardrail_url="http://guard.local",
        guardrail_api_key="guard-test",
        **extra,
    )


def test_gateway_rejects_conflicting_keys():
    with pytest.raises(ValueError, match="direct key"):
        Settings(
            _env_file=None,
            rag_mode="real",
            llm_provider="openai",
            embedding_provider="openai",
            openai_api_key="direct-secret",
            litellm_api_key="virtual-key",
        )


@pytest.mark.parametrize("body", [{}, {"allowed": "true"}, {"allowed": None}])
def test_invalid_guard_response_fails_closed(body):
    with config(), patch("app.services.guardrails.httpx.Client") as client:
        client.return_value.__enter__.return_value.post.return_value.json.return_value = body
        with pytest.raises(GuardrailUnavailable):
            check("ordinary question", "input")


def test_guard_timeout_fails_closed_without_error_body():
    with config(), patch("app.services.guardrails.httpx.Client") as client:
        client.return_value.__enter__.return_value.post.side_effect = httpx.ReadTimeout(
            "private content"
        )
        with pytest.raises(GuardrailUnavailable) as exc:
            check("ordinary question", "input")
        assert "private" not in str(exc.value)


def test_unsafe_context_is_removed_from_generation_and_response():
    contexts = [
        {"chunk_text": "unsafe", "source": "poison.md"},
        {"chunk_text": "safe", "source": "guide.md"},
    ]

    def boundary(text, phase):
        if text == "unsafe":
            raise PolicyBlocked()

    with patch("app.services.guardrails.check", side_effect=boundary):
        assert safe_contexts(contexts) == contexts[1:]
        with pytest.raises(PolicyBlocked):
            safe_contexts(contexts[:1])


def test_input_block_happens_before_retrieval():
    with (
        patch("app.routers.chat.check", side_effect=PolicyBlocked()),
        patch("app.routers.chat.retrieve") as retrieve,
    ):
        response = TestClient(app).post("/chat", json={"question": "attack"})
    assert response.status_code == 422
    assert response.json()["code"] == "policy_blocked"
    retrieve.assert_not_called()


def test_output_block_cannot_return_answer_or_context():
    contexts = [
        {
            "document_id": 1,
            "chunk_text": "synthetic source",
            "source": "guide.md",
            "distance": 0.1,
        }
    ]
    with (
        patch("app.routers.chat.check", side_effect=[None, PolicyBlocked()]),
        patch("app.routers.chat.retrieve", return_value=contexts),
        patch("app.routers.chat.safe_contexts", return_value=contexts),
        patch("app.routers.chat.generate", return_value={"answer": "DAY6_SECRET_TEST"}),
    ):
        response = TestClient(app).post("/chat", json={"question": "allowed"})
    assert response.status_code == 422
    assert (
        "DAY6_SECRET" not in response.text and "synthetic source" not in response.text
    )
