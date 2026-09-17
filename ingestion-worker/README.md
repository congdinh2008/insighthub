# Ingestion worker - Day 01

ARQ 0.28.0 + Redis 7, Python 3.12, shared `api/app/services/ingestion.py`. Build context là repo root; Dockerfile không nhân bản pipeline và chạy non-root.

- Queue mặc định `insighthub:ingestion`; stable job ID `ingestion:{document_id}`; payload expire 24 giờ.
- `max_jobs=2`, timeout 120s, drain 125s, Compose grace 150s.
- Transient provider errors: initial attempt + 3 retries, backoff 1/2/4s. Invalid vectors/input/identity không retry.
- JSON logs theo allowlist, không job arguments/provider bodies. Metrics counter/histogram từ các attempts thực.
- Internal HTTP :8081: `/healthz`, `/readyz` (Redis heartbeat + DB), `/metrics`; không publish host port.
- Healthcheck kiểm tra readiness của chính process worker. ARQ sở hữu signals; HTTP server dùng chung loop/lifecycle.
- `make test-image && make test-worker` chạy tests trong runner tạm, không thêm service mặc định.

[Architecture và giới hạn](../docs/day1/Architecture_and_Decisions.md), [runbook](../docs/day1/Runbook.md), [review/evidence](../docs/day1/Review_and_Self_Check.md).
