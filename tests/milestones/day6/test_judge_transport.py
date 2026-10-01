"""Transient evaluator transport errors never weaken the security oracle."""

import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/security/day6"))
import evaluate  # noqa: E402


def invoke(monkeypatch, tmp_path, responses):
    calls = []

    def handle(request):
        calls.append(request)
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(evaluate.time, "sleep", lambda _: None)
    monkeypatch.setenv("DAY6_RESULT_LOG", str(tmp_path / "results.jsonl"))
    client = httpx.Client(transport=httpx.MockTransport(handle))

    def run():
        with client:
            return evaluate.judge_transport(
                client,
                "http://evaluator-test/completions",
                headers={"Authorization": "Bearer synthetic-only"},
                payload={"messages": ["synthetic input"]},
                case_id="synthetic-case",
                parent_id="synthetic-parent",
            )

    return run, calls


@pytest.mark.parametrize("status", [400, 401, 422, 429])
def test_denials_are_not_retried(monkeypatch, tmp_path, status):
    run, calls = invoke(monkeypatch, tmp_path, [httpx.Response(status)])
    with pytest.raises(httpx.HTTPStatusError):
        run()
    assert len(calls) == 1


@pytest.mark.parametrize("failure", [httpx.Response(500), httpx.ReadTimeout("timeout")])
def test_one_transient_retry_preserves_negative_verdict(monkeypatch, tmp_path, failure):
    verdict = {"safe": False, "grounded": False, "reason": "Unsafe answer"}
    run, calls = invoke(
        monkeypatch, tmp_path, [failure, httpx.Response(200, json=verdict)]
    )
    response, attempts = run()
    assert response.json() == verdict
    assert len(calls) == len(attempts) == 2
    assert calls[0].content == calls[1].content
    log = (tmp_path / "judge-transport.jsonl").read_text()
    assert json.loads(log)["retry"] is True
    assert "synthetic-only" not in log and "synthetic input" not in log


def test_repeated_upstream_failure_is_still_an_error(monkeypatch, tmp_path):
    run, calls = invoke(
        monkeypatch, tmp_path, [httpx.Response(503), httpx.Response(503)]
    )
    with pytest.raises(httpx.HTTPStatusError):
        run()
    assert len(calls) == 2
    rows = (tmp_path / "judge-transport.jsonl").read_text().splitlines()
    assert [json.loads(row)["retry"] for row in rows] == [True, False]


def test_valid_or_malformed_200_is_never_regraded(monkeypatch, tmp_path):
    run, calls = invoke(monkeypatch, tmp_path, [httpx.Response(200, text="not JSON")])
    response, attempts = run()
    with pytest.raises(ValueError):
        response.json()
    assert len(calls) == len(attempts) == 1
