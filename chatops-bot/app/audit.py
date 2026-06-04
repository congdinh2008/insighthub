"""Audit log — appends NDJSON records to chatops-audit.log for every tool call."""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("chatops-bot.audit")

AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "chatops-audit.log"))


def log_tool_call(
    user: str,
    tool: str,
    args: dict,
    result_summary: str,
    approved: bool = True,
) -> None:
    """Append one NDJSON audit record for each tool call or permission decision."""
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "user": user,
        "tool": tool,
        "args": args,
        "result": result_summary[:500],
        "approved": approved,
    }
    line = json.dumps(record, ensure_ascii=False)
    try:
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as exc:
        logger.error("Failed to write audit log to %s: %s", AUDIT_LOG_PATH, exc)
    logger.info("AUDIT %s", line)
