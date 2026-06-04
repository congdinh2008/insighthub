"""Tests for Slack signature verification and replay attack defense."""
import hashlib
import hmac
import time

import pytest
from fastapi import HTTPException

TEST_SECRET = "test-secret-for-signing"


def _make_slack_headers(body: str, secret: str = TEST_SECRET, ts_offset: int = 0) -> dict:
    ts = str(int(time.time()) + ts_offset)
    sig_base = f"v0:{ts}:{body}"
    sig = "v0=" + hmac.new(secret.encode(), sig_base.encode(), hashlib.sha256).hexdigest()
    return {"x-slack-request-timestamp": ts, "x-slack-signature": sig}


class TestVerifySlackSignature:
    def test_valid_signature_passes(self):
        from app.main import verify_slack_signature
        body = b'{"type":"event_callback"}'
        headers = _make_slack_headers(body.decode())
        verify_slack_signature(headers, body, TEST_SECRET)  # must not raise

    def test_invalid_signature_rejected(self):
        from app.main import verify_slack_signature
        body = b'{"type":"event_callback"}'
        headers = {**_make_slack_headers(body.decode()), "x-slack-signature": "v0=deadbeef"}
        with pytest.raises(HTTPException) as exc:
            verify_slack_signature(headers, body, TEST_SECRET)
        assert exc.value.status_code == 401

    def test_old_timestamp_rejected(self):
        """Replay attack defense: reject requests with timestamp > 5 min old."""
        from app.main import verify_slack_signature
        body = b'{"type":"event_callback"}'
        headers = _make_slack_headers(body.decode(), ts_offset=-400)  # 400s ago
        with pytest.raises(HTTPException) as exc:
            verify_slack_signature(headers, body, TEST_SECRET)
        assert exc.value.status_code == 401

    def test_future_timestamp_rejected(self):
        """Also reject significantly future timestamps."""
        from app.main import verify_slack_signature
        body = b'{"type":"event_callback"}'
        headers = _make_slack_headers(body.decode(), ts_offset=400)  # 400s in future
        with pytest.raises(HTTPException) as exc:
            verify_slack_signature(headers, body, TEST_SECRET)
        assert exc.value.status_code == 401

    def test_missing_headers_rejected(self):
        from app.main import verify_slack_signature
        body = b'{"type":"event_callback"}'
        with pytest.raises(HTTPException) as exc:
            verify_slack_signature({}, body, TEST_SECRET)
        assert exc.value.status_code == 401

    def test_missing_signature_header(self):
        from app.main import verify_slack_signature
        body = b'{"type":"event_callback"}'
        ts = str(int(time.time()))
        headers = {"x-slack-request-timestamp": ts}
        with pytest.raises(HTTPException) as exc:
            verify_slack_signature(headers, body, TEST_SECRET)
        assert exc.value.status_code == 401

    def test_tampered_body_rejected(self):
        from app.main import verify_slack_signature
        original = b'{"type":"event_callback"}'
        tampered = b'{"type":"event_callback","injected":"evil"}'
        headers = _make_slack_headers(original.decode())
        with pytest.raises(HTTPException):
            verify_slack_signature(headers, tampered, TEST_SECRET)


class TestHealthEndpoint:
    def test_healthz_returns_ok(self, bot_client):
        resp = bot_client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_healthz_has_service_field(self, bot_client):
        resp = bot_client.get("/healthz")
        assert "service" in resp.json()


class TestUrlVerification:
    def test_url_verification_challenge(self, bot_client):
        payload = {"type": "url_verification", "challenge": "abc123"}
        resp = bot_client.post("/slack/events", json=payload)
        assert resp.status_code == 200
        assert resp.json()["challenge"] == "abc123"
