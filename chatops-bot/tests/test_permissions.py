"""Tests for 3-tier permission system."""
import time

import pytest
from app.permissions import (
    PermissionTier,
    classify_intent,
    issue_confirmation_token,
    validate_confirmation_token,
)


class TestClassifyIntent:
    def test_health_question_is_read(self):
        assert classify_intent("InsightHub có healthy không?") == PermissionTier.READ
        assert classify_intent("api healthy?") == PermissionTier.READ
        assert classify_intent("Is everything OK?") == PermissionTier.READ

    def test_pod_status_is_read(self):
        assert classify_intent("Pod nào đang lỗi?") == PermissionTier.READ
        assert classify_intent("which pods are failing?") == PermissionTier.READ

    def test_ingest_count_is_read(self):
        assert classify_intent("Hôm nay ingest bao nhiêu doc?") == PermissionTier.READ
        assert classify_intent("how many documents today?") == PermissionTier.READ

    def test_scale_is_write(self):
        assert classify_intent("Scale api to 5 replicas") == PermissionTier.WRITE
        assert classify_intent("scale api lên 3") == PermissionTier.WRITE

    def test_restart_is_write(self):
        assert classify_intent("Restart worker pod") == PermissionTier.WRITE

    def test_stop_is_write(self):
        assert classify_intent("Stop the api service") == PermissionTier.WRITE

    def test_delete_is_destructive(self):
        assert classify_intent("Delete pod api-0") == PermissionTier.DESTRUCTIVE

    def test_drop_is_destructive(self):
        assert classify_intent("Drop the database") == PermissionTier.DESTRUCTIVE

    def test_terminate_is_destructive(self):
        assert classify_intent("terminate all pods") == PermissionTier.DESTRUCTIVE


class TestConfirmationToken:
    def test_issue_and_validate_token(self):
        user = "U12345"
        token = issue_confirmation_token(user)
        assert isinstance(token, str) and len(token) > 0
        assert validate_confirmation_token(token, user) is True

    def test_token_consumed_after_use(self):
        user = "U12345"
        token = issue_confirmation_token(user)
        assert validate_confirmation_token(token, user) is True
        assert validate_confirmation_token(token, user) is False  # consumed

    def test_wrong_user_rejected(self):
        token = issue_confirmation_token("U12345")
        assert validate_confirmation_token(token, "U99999") is False

    def test_invalid_token_rejected(self):
        assert validate_confirmation_token("not-a-real-token", "U12345") is False

    def test_expired_token_rejected(self, monkeypatch):
        import app.permissions as perm_mod
        monkeypatch.setattr(perm_mod, "TOKEN_TTL_SECONDS", 0)
        token = issue_confirmation_token("U12345")
        # Wait a tiny bit to ensure expiry
        import time; time.sleep(0.01)
        assert validate_confirmation_token(token, "U12345") is False

    def test_multiple_tokens_independent(self):
        token_a = issue_confirmation_token("UA")
        token_b = issue_confirmation_token("UB")
        assert validate_confirmation_token(token_a, "UA") is True
        assert validate_confirmation_token(token_b, "UB") is True
