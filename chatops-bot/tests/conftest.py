"""Shared pytest fixtures for ChatOps bot tests."""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_audit_log(tmp_path, monkeypatch):
    """Redirect audit log to a temp file so tests don't pollute chatops-audit.log."""
    log_path = tmp_path / "test-audit.log"
    monkeypatch.setenv("AUDIT_LOG_PATH", str(log_path))
    import app.audit as audit_mod
    audit_mod.AUDIT_LOG_PATH = log_path
    yield log_path
    # cleanup: monkeypatch restores the env var automatically


@pytest.fixture
def bot_client():
    """TestClient with a blank signing secret (skips sig verification in tests)."""
    os.environ.pop("SLACK_SIGNING_SECRET", None)
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def signed_bot_client(monkeypatch):
    """TestClient with a known signing secret for signature tests."""
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret-for-signing")
    from app.main import app
    with TestClient(app) as c:
        yield c
