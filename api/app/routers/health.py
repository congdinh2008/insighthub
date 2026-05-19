"""Readiness checks schema, dimension and identity; it does not call paid providers."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.db import healthcheck

router = APIRouter(tags=["health"])


@router.get("/healthz")
def liveness():
    return {"status": "ok", "mode": get_settings().rag_mode}


@router.get("/readyz")
def readiness():
    if not healthcheck():
        return JSONResponse(
            status_code=503, content={"status": "not_ready", "db": False}
        )
    return {"status": "ready", "db": True, "mode": get_settings().rag_mode}
