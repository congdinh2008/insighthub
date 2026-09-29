FROM ghcr.io/berriai/litellm:v1.103.0@sha256:bd089afdcd35b894b14a93f9743cdc8b591f82da1a38dd43a010a7b0c9de5fd7
COPY hooks.py /app/day6_hooks.py
COPY exporter.py /app/day6_exporter.py
COPY config.yaml /app/day6-config.yaml
ENV PYTHONPATH=/app LITELLM_TELEMETRY=false LITELLM_LOG=ERROR
CMD ["--config", "/app/day6-config.yaml", "--port", "4000", "--num_workers", "1"]
