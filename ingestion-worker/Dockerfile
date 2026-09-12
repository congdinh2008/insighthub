FROM python:3.12.14-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY api/requirements.txt /deps/api/requirements.txt
COPY ingestion-worker/requirements.txt /deps/ingestion-worker/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install --timeout 120 --retries 3 --require-hashes -r /deps/ingestion-worker/requirements.txt \
    && groupadd --system --gid 1001 appuser \
    && useradd --system --uid 1001 --gid appuser appuser
COPY --chown=appuser:appuser api/app ./app
COPY --chown=appuser:appuser ingestion-worker/worker.py .
USER appuser
CMD ["arq", "worker.WorkerSettings"]
