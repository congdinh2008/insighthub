FROM python:3.12.14-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DO_NOT_TRACK=1 NEMO_GUARDRAILS_NO_USAGE_STATS=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
RUN groupadd --gid 1001 app && useradd --uid 1001 --gid app --create-home app
COPY --chown=app:app service.py config.yaml ./
USER app
EXPOSE 8082
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8082", "--no-access-log"]
