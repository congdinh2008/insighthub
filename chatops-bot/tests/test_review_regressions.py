"""Regression cases discovered during the Day 05 completion review."""
import asyncio
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings  # noqa: E402
from app.intents import _pod_rows, _scalar, answer, failing_pods  # noqa: E402
from app.permissions import route  # noqa: E402
from app.worker import process  # noqa: E402


def test_prometheus_scientific_scalar_and_missing_samples():
    assert _scalar({"result": "{} => 1.2e-05 @[1790]"}) == 1.2e-5
    assert _scalar({"result": "{} => NaN @[1790]"}) is None
    assert _scalar({"result": "{} => +Inf @[1790]"}) is None
    assert _scalar({"result": ""}) is None
    assert _scalar({"result": "{} => 1e309 @[1790]"}) is None


def test_pending_init_failure_and_completed_job():
    pods = {"items": [
        {"metadata": {"name": "pending-api"}, "status": {"phase": "Pending"}},
        {"metadata": {"name": "init-failed"}, "status": {"phase": "Pending",
         "initContainerStatuses": [{"ready": False, "state": {"waiting": {"reason": "ImagePullBackOff"}}}]}},
        {"metadata": {"name": "done-job"}, "status": {"phase": "Succeeded",
         "containerStatuses": [{"ready": False, "state": {"terminated": {"reason": "Completed", "exitCode": 0}}}]}},
    ]}
    failed = failing_pods(pods)
    assert any("pending-api" in item for item in failed)
    assert any("ImagePullBackOff" in item for item in failed)
    assert not any("done-job" in item for item in failed)


@pytest.mark.parametrize("payload", [{"items": [{}]}, [{"error": "Forbidden"}], {"items": ["bad"]}])
def test_malformed_pod_response_never_becomes_healthy(payload):
    with pytest.raises(ValueError):
        _pod_rows(payload)


def test_no_metrics_does_not_invent_zero(monkeypatch):
    async def get(*args):
        return {"status": "ready", "db": True}
    async def mcp(config, backend, tool, arguments):
        if backend == "kubernetes":
            return {"items": [{"metadata": {"name": "api"}, "status": {"phase": "Running"}}]}
        assert "or vector(0)" not in arguments["query"]
        return {"result": ""}
    monkeypatch.setattr("app.intents._fixed_get", get)
    monkeypatch.setattr("app.intents.call", mcp)
    result, _ = asyncio.run(answer("health", Settings.from_env()))
    assert "unknown/partial" in result


@pytest.mark.parametrize("text", ["scale api to 2.5", "scale api to 2 then scale api to 5", "confirm abcdefghijklmnopqrstuvwxyz and scale api to 3"])
def test_ambiguous_mutation_commands_are_denied(text):
    assert route(text)[0] in {"denied", "unknown"}


def test_scale_timeout_has_clear_uncertain_reply(monkeypatch, tmp_path):
    async def consume(*args, **kwargs):
        return {"operation_id": "test-op", "replicas": 2}
    async def timeout(*args):
        raise TimeoutError()
    monkeypatch.setattr("app.worker.consume_approval", consume)
    monkeypatch.setattr("app.worker.scale_api", timeout)
    settings = replace(Settings.from_env(), audit_path=str(tmp_path / "audit.jsonl"))
    event = dict(event_id="EvTest", user="U_TEST", workspace="T_TEST", channel="C_TEST", thread="1.2",
                 text="confirm abcdefghijklmnopqrstuvwxyz")
    reply = asyncio.run(process(event, settings, None))
    assert "Kiểm deployment" in reply
