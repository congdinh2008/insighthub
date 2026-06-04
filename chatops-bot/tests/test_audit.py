"""Tests for audit logging — NDJSON format with required fields."""
import json
from pathlib import Path


class TestAuditLog:
    def test_writes_ndjson_record(self, isolated_audit_log):
        import app.audit as audit_mod
        audit_mod.log_tool_call("U123", "check_api_health", {}, "status: ok")
        assert isolated_audit_log.exists()
        lines = isolated_audit_log.read_text().strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["user"] == "U123"
        assert record["tool"] == "check_api_health"
        assert record["approved"] is True

    def test_record_has_all_required_fields(self, isolated_audit_log):
        """verify-day-5.sh checks: .ts and .user and .tool"""
        import app.audit as audit_mod
        audit_mod.log_tool_call("U456", "get_failing_pods", {"namespace": "insighthub"}, "2 failing pods")
        line = isolated_audit_log.read_text().strip()
        record = json.loads(line)
        for field in ("ts", "user", "tool", "args", "result", "approved"):
            assert field in record, f"Missing field: {field}"

    def test_multiple_calls_appended(self, isolated_audit_log):
        import app.audit as audit_mod
        audit_mod.log_tool_call("U1", "check_api_health", {}, "ok")
        audit_mod.log_tool_call("U2", "get_failing_pods", {}, "none failing")
        lines = isolated_audit_log.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_disapproved_action_logged(self, isolated_audit_log):
        import app.audit as audit_mod
        audit_mod.log_tool_call("U123", "permission_check", {"tier": "destructive"}, "denied", approved=False)
        record = json.loads(isolated_audit_log.read_text().strip())
        assert record["approved"] is False

    def test_timestamp_is_iso_format(self, isolated_audit_log):
        from datetime import datetime
        import app.audit as audit_mod
        audit_mod.log_tool_call("U1", "tool", {}, "result")
        record = json.loads(isolated_audit_log.read_text().strip())
        ts = record["ts"]
        parsed = datetime.fromisoformat(ts)
        assert parsed is not None

    def test_result_truncated_at_500_chars(self, isolated_audit_log):
        import app.audit as audit_mod
        long_result = "x" * 1000
        audit_mod.log_tool_call("U1", "tool", {}, long_result)
        record = json.loads(isolated_audit_log.read_text().strip())
        assert len(record["result"]) <= 500
