FROM python:3.12.14-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
WORKDIR /app
FROM base AS deps
COPY ingestion-worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt
FROM base AS runtime
RUN groupadd --system --gid 1001 appuser && useradd --system --uid 1001 --gid appuser appuser
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY --chown=appuser:appuser api/app ./app
COPY --chown=appuser:appuser ingestion-worker/worker.py ./worker.py
USER appuser
EXPOSE 8081
HEALTHCHECK --interval=5s --timeout=3s --start-period=15s --retries=6 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/readyz', timeout=2)"
CMD ["python", "worker.py"]
FROM runtime AS test
USER root
COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip install --no-cache-dir --require-hashes -r /tmp/requirements-dev.txt
WORKDIR /workspace
CMD ["python", "-m", "pytest"]
