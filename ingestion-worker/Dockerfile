# Day 1 worker image: it owns the ARQ process but imports the one shared pipeline.
FROM python:3.12.14-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS deps
WORKDIR /deps/worker
COPY api/requirements.txt /deps/api/requirements.txt
COPY ingestion-worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

FROM python:3.12.14-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser appuser \
    && mkdir -p /app/payloads \
    && chown appuser:appuser /app/payloads \
    && chmod 700 /app/payloads
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY --chown=appuser:appuser api/app ./app
COPY --chown=appuser:appuser ingestion-worker/worker.py ./ingestion_worker/worker.py
USER appuser
CMD ["arq", "ingestion_worker.worker.WorkerSettings"]
