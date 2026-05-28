# InsightHub — Ingestion Worker Dockerfile
#
# Build context: repo root (docker compose build context: .)
# Reuses api/requirements.txt — worker chia sẻ Python deps với API,
# chỉ khác CMD: arq thay vì uvicorn.
#
# Build:
#   docker compose build ingestion-worker
# Chạy:
#   docker compose up ingestion-worker

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

FROM base AS deps
COPY ingestion-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
RUN groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser appuser

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy shared app code từ api/ (process_document, embeddings, db, config, metrics)
COPY --chown=appuser:appuser api/app ./app

# Copy worker-specific code
COPY --chown=appuser:appuser ingestion-worker/worker ./worker

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import redis; r=redis.from_url('${REDIS_URL:-redis://redis:6379}'); r.ping()" || exit 1

CMD ["arq", "worker.settings.WorkerSettings"]
