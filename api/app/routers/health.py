"""Readiness checks schema, dimension and identity; it does not call paid providers."""

import asyncio
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.db import healthcheck
from app.services.queue import queue_healthcheck

router = APIRouter(tags=["health"])


@router.get("/healthz")
def liveness() -> dict[str, str]:
    return {"status": "ok", "mode": get_settings().rag_mode}


@router.get("/readyz", response_model=None)
def readiness() -> dict[str, Any] | JSONResponse:
    if not healthcheck() or not asyncio.run(queue_healthcheck()):
        return JSONResponse(
            status_code=503, content={"status": "not_ready", "db": False}
        )
    return {"status": "ready", "db": True, "mode": get_settings().rag_mode}
