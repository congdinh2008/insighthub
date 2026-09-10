# CLAUDE.md — InsightHub

## 1. Architecture
- Stack: Next.js 16 (web) + FastAPI/Python 3.12 (api) + PostgreSQL 16/pgvector 0.8.2 + Redis + ingestion-worker (ARQ)
- v0 hiện tại: 3 service trong docker-compose.yml (web, api, postgres); ingestion chạy đồng bộ trong request (api/app/services/ingestion.py)
- v1 mục tiêu Day 1: 5 service — thêm redis + ingestion-worker; api trả 202 và enqueue job thay vì xử lý đồng bộ
- Boundaries: api KHÔNG giữ state ingestion ngoài enqueue; `POST /chat` (retrieval + generation) luôn ở api, không qua worker; ingestion-worker sở hữu chunk/embed/store và phải tái dùng đúng contract idempotency của `process_document`

## 2. Conventions
- Python: type hints bắt buộc (api/app/core/config.py, app/services/*); chưa có ruff/mypy config trong repo — không tự thêm lint tool mới ngoài phạm vi task
- REST adapters dùng `httpx`, không dùng `requests` (ghi rõ trong api/requirements.in)
- Lỗi nghiệp vụ kế thừa `ServiceError` (api/app/core/errors.py): status_code/code/message cố định, không lộ raw provider error hoặc nội dung tài liệu riêng tư
- Config qua `pydantic_settings.Settings`, `frozen=True`, cache bằng `lru_cache`; validate tổ hợp mode/provider ngay lúc khởi động
- Test dùng `unittest` (api/tests, tests/), không phải pytest; test luôn ép `RAG_MODE=fixture` (api/tests/support.py), không gọi provider thật/tốn phí

## 3. Commands
- Run local:
`docker compose up --build -d --wait` (hoặc `make up`)
- Dừng, giữ volume:
`make down`
- Test:
`make test-backend` (unit + integration trong container api), `make test-verifiers` (verifier regression), `make test-mcp` (MCP SDK + smoke); `make test` chạy cả ba
- Test một file/class:
`docker compose exec api python -m unittest api.tests.test_unit_config -v`
- Smoke end-to-end:
`make smoke`
- Web:
`npm run dev|build|start|typecheck --prefix web`
- Verify theo ngày (Day N):
`bash scripts/verify-day-N.sh` theo tham số/evidence trong scripts/VERIFICATION_CONTRACT.md
- Migration: không có Alembic; schema thuần SQL tại `infra/db/init.sql`, chỉ áp dụng trên volume mới (guard trong file chặn chạy lại trên schema cũ)

## 4. Constraints
- KHÔNG hardcode secret — chỉ qua env var (.env, đã trong .gitignore); không commit API key, tfstate, kubeconfig
- KHÔNG đổi DB schema hoặc bỏ assertion chỉ để làm test xanh
- KHÔNG dùng `requests` — REST adapters dùng `httpx`
- Real provider (`RAG_MODE=real`) KHÔNG fallback âm thầm sang fixture khi thiếu key hoặc provider lỗi
- Đổi embedding provider/model/dimension/endpoint/revision cần migration/reindex — không tự sửa vector để né lỗi identity
- Retry cùng document id + cùng bytes + cùng pipeline không được tạo chunk trùng; giữ nguyên error contract hiện có
- KHÔNG `git push --force` lên main

## 5. Domain knowledge
- Document đi qua extract → chunk → embed → store; `documents.status`: `pending → ready | failed` (CHECK constraint trong infra/db/init.sql); `ready` bắt buộc chunk_count > 0, content_sha256, pipeline_id, embedding_identity_id và error_code NULL
- LLM và embedding provider tách biệt, chọn qua `LLM_PROVIDER`/`EMBEDDING_PROVIDER`: `fixture` (mặc định, không cần key) hoặc real (`gemini`/`anthropic`/`openai`/`ollama` cho chat; `gemini`/`voyage`/`openai`/`ollama` cho embedding)
- Embedding: `EMBEDDING_DIM=1024` mặc định, khớp `VECTOR(1024)` trong schema; `embedding_index` là bảng singleton khoá identity (provider/model/dim/endpoint/revision) theo lần ingest thành công đầu tiên — identity lệch trả 409 `index_identity_conflict`
- Retry cùng id + cùng bytes + cùng pipeline sau khi `ready` là no-op, trả lại chunk_count cũ; lệch filename/content/pipeline trên cùng id trả 409 `document_conflict`
- `POST /chat` trả 404 khi chưa có tài liệu nào `ready`

## 6. References
- README.md, GETTING_STARTED.md, Running-Project-Specification-Student.md
- AGENTS.md — nguồn context sáu section chung cho mọi coding host (Claude Code/ChatGPT-Codex/Antigravity); giữ đồng bộ với file này khi cập nhật
- scripts/VERIFICATION_CONTRACT.md — hợp đồng verifier từng ngày
- docs/Guide_Coding_Host_DO2603.md, docs/Guide_Local_AWS_Cost_DO2603.md
