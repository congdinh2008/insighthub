"""Structured JSON stdout logs. scripts/verify.py greps `ingestion_completed` from `docker compose logs`."""

import json
import logging
import sys
from datetime import datetime, timezone

logger = logging.getLogger("insighthub.worker")


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.handlers = [handler]
    logger.setLevel(level)
    logger.propagate = False


def log_event(event: str, **fields) -> None:
    logger.info(
        json.dumps(
            {
                "event": event,
                "timestamp": datetime.now(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
                **fields,
            }
        )
    )
