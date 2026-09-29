"""Small, append-only JSON audit for the bounded Day 05 lab."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def record(path: str, *, event_id: str, user: str, action: str,
           decision: str, **details: Any) -> dict[str, Any]:
    if decision not in {"allowed", "denied", "approval_required"}:
        raise ValueError("invalid audit decision")
    entry: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event_id": event_id,
        "user": user,
        "action": action,
        "decision": decision,
    }
    if os.getenv("INSIGHTHUB_VERIFY_RUN_ID"):
        entry["test_run_id"] = os.environ["INSIGHTHUB_VERIFY_RUN_ID"]
    entry.update(details)
    parent = Path(path).parent
    parent.mkdir(parents=True, exist_ok=True)
    line = (json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    if len(line) > 4096:
        raise ValueError("audit record too large")
    fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    try:
        os.write(fd, line)
        os.fsync(fd)
    finally:
        os.close(fd)
    return entry
