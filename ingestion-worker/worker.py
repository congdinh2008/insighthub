"""Day 01 ARQ worker: idempotent ingestion, bounded retries, safe telemetry."""

import asyncio
import json
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import uvicorn
from app.core.config import get_settings
from app.core.db import close_pool, get_conn, healthcheck, initialize_database
from app.core.errors import DocumentNotFound, ProviderError, ServiceError
from app.services.ingestion import process_document
from app.services.queue import redis_settings
from arq import Retry
from arq.worker import Worker
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from redis.exceptions import RedisError

logger = logging.getLogger("insighthub.worker")
job_outcomes = Counter("insighthub_worker_jobs_total", "Worker outcomes", ["outcome"])
job_duration = Histogram("insighthub_worker_job_seconds", "Ingestion attempt duration")
monitor = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
worker_context: dict[str, Any] = {}


class SafeJSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", "runtime_log"),
        }
        for key in (
            "document_id",
            "job_id",
            "attempt",
            "status",
            "duration_seconds",
            "error_code",
            "defer_seconds",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        # Deliberately never format arguments, arbitrary messages or traceback text.
        return json.dumps(payload, ensure_ascii=False)


def event(name: str, **fields: Any) -> None:
    logger.info("", extra={"event": name, **fields})


@monitor.get("/healthz")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@monitor.get("/readyz")
async def readiness() -> JSONResponse:
    ready = False
    try:
        pool = worker_context["redis"]
        heartbeat = await asyncio.wait_for(
            pool.exists(get_settings().queue_name + ":health-check"), timeout=1
        )
        ready = bool(heartbeat) and await asyncio.to_thread(healthcheck)
    except Exception:
        ready = False
    return JSONResponse(
        {"status": "ready" if ready else "not_ready"}, status_code=200 if ready else 503
    )


@monitor.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), headers={"Content-Type": CONTENT_TYPE_LATEST})


class MonitorServer(uvicorn.Server):
    @contextmanager
    def capture_signals(self) -> Iterator[None]:
        # ARQ owns signals; the monitor shares its event loop and lifecycle.
        yield


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(SafeJSONFormatter())
    logging.getLogger().handlers = [handler]
    logging.getLogger().setLevel(logging.INFO)
    for name in ("arq", "httpx", "httpcore", "psycopg.pool", "pypdf"):
        logging.getLogger(name).setLevel(logging.CRITICAL)


async def startup(ctx: dict[str, Any]) -> None:
    await asyncio.to_thread(initialize_database)
    worker_context.update(ctx)
    server = MonitorServer(
        uvicorn.Config(
            monitor, host="0.0.0.0", port=8081, access_log=False, log_config=None
        )
    )
    ctx["monitor_server"] = server
    ctx["monitor_task"] = asyncio.create_task(server.serve())
    event("worker_started")


async def shutdown(ctx: dict[str, Any]) -> None:
    server: MonitorServer = ctx["monitor_server"]
    server.should_exit = True
    await ctx["monitor_task"]
    await asyncio.to_thread(close_pool)
    worker_context.clear()
    event("worker_stopped")


def fail_pending(document_id: int, code: str) -> None:
    # Some invariant errors occur before process_document's savepoint. Keep the
    # asynchronous outcome truthful without overwriting a concurrent success.
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET status='failed', error_code=%s WHERE id=%s AND status='pending'",
            (code, document_id),
        )


async def ingest(
    ctx: dict[str, Any], document_id: int, filename: str, content: bytes
) -> int:
    attempt = int(ctx["job_try"])
    fields = {
        "document_id": document_id,
        "job_id": str(ctx["job_id"]),
        "attempt": attempt,
    }
    started = time.monotonic()
    event("ingestion_started", **fields, status="pending")
    work = asyncio.create_task(
        asyncio.to_thread(
            process_document,
            document_id,
            filename,
            content,
            retry_pending=attempt < 4,
        )
    )
    try:
        # Cancellation of an asyncio future cannot stop the sync DB/provider thread.
        # Drain it before shutdown closes the pool, then let ARQ redeliver safely.
        try:
            count = await asyncio.shield(work)
        except asyncio.CancelledError:
            try:
                await work
            except Exception:
                pass
            event("ingestion_interrupted", **fields)
            raise
        job_outcomes.labels("ready").inc()
        event(
            "ingestion_completed",
            **fields,
            status="ready",
            duration_seconds=round(time.monotonic() - started, 6),
        )
        return count
    except ProviderError as exc:
        if exc.retryable and attempt < 4:
            delay = 2 ** (attempt - 1)
            job_outcomes.labels("retry").inc()
            event(
                "ingestion_retry",
                **fields,
                status="pending",
                error_code=exc.code,
                defer_seconds=delay,
            )
            raise Retry(defer=delay) from None
        job_outcomes.labels("failed").inc()
        event("ingestion_failed", **fields, status="failed", error_code=exc.code)
        return 0
    except DocumentNotFound:
        job_outcomes.labels("deleted").inc()
        event(
            "ingestion_discarded",
            **fields,
            status="deleted",
            error_code="document_not_found",
        )
        return 0
    except ServiceError as exc:
        await asyncio.to_thread(fail_pending, document_id, exc.code)
        job_outcomes.labels("failed").inc()
        event("ingestion_failed", **fields, status="failed", error_code=exc.code)
        return 0
    finally:
        job_duration.observe(time.monotonic() - started)


class WorkerSettings:
    functions = [ingest]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings()
    queue_name = get_settings().queue_name
    max_tries = 4
    max_jobs = get_settings().worker_max_jobs
    job_timeout = get_settings().worker_job_timeout
    job_completion_wait = get_settings().worker_shutdown_wait
    keep_result = 0
    log_results = False
    health_check_interval = 2
    health_check_key = queue_name + ":health-check"
    poll_delay = 0.1


def main() -> int:
    # Configure before connecting so startup failures also use safe JSON logs.
    configure_logging()
    try:
        Worker(
            **{k: v for k, v in vars(WorkerSettings).items() if not k.startswith("_")}
        ).run()
    except (RedisError, OSError):
        # Docker restarts the process; never expose connection credentials/body.
        logger.error(
            "",
            extra={
                "event": "worker_connection_lost",
                "error_code": "queue_unavailable",
            },
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
