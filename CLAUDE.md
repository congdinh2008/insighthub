# CLAUDE.md — InsightHub

> AI agent đọc file này mỗi phiên. Giữ ≤ 200 dòng, cô đọng.
> Cập nhật sau mỗi Day refactor.

## Architecture

InsightHub — RAG Notebook (giống Google NotebookLM). Upload PDF/MD/TXT → chunk + embed → pgvector → hỏi đáp bằng LLM.

**v1 (Day 1) — 5 services:**

| Service | Image/Build | Port | Role |
|---|---|---|---|
| postgres | pgvector/pgvector:0.8.2-pg16 | 5432 | Vector DB + metadata |
| redis | redis:7-alpine | 6379 | ARQ job queue |
| api | ./api | 8000 | FastAPI: upload → enqueue, /chat retrieve+generate |
| ingestion-worker | ./ingestion-worker (root ctx) | — | ARQ worker: chunk+embed+store |
| web | ./web | 3000 | Next.js 15 App Router dashboard |

**Data flow:**
```
web → POST /documents → api → enqueue(redis) → ingestion-worker → postgres+pgvector
web → POST /chat → api → retrieve(pgvector) + generate(LLM) → response
```

**LLM providers:** gemini (default, free) | anthropic | ollama | bedrock
**Embedding providers:** gemini (default) | voyage | openai | ollama | local (hash fallback)

## Conventions

- Python: PEP 8, type hints bắt buộc, `ruff format` trước commit
- Commit: Conventional Commits — `feat:`, `fix:`, `refactor:`, `chore:`
- Branch: `dayN-<topic>` (vd: `day1-refactor`)
- PR title: `[Day N] <mô tả ngắn>`
- Secrets: luôn dùng env var, không hardcode
- Logging: `logger = logging.getLogger("insighthub.<module>")`

## Commands

```bash
# Stack
docker compose up --build          # start toàn bộ 5 service
docker compose logs -f api         # xem log api
docker compose logs -f ingestion-worker  # xem log worker

# Verify
bash scripts/verify-day-1.sh      # kiểm tra Day 1 artifact
bash scripts/smoke-test.sh         # smoke test 6 check

# Dev
cd api && pytest -xvs              # chạy tests
cd api && ruff format .            # format code
cd api && ruff check .             # lint
```

## Constraints

- **EMBEDDING_DIM phải khớp VECTOR(n) trong infra/db/init.sql** (hiện tại: 1024).
  Đổi provider sang OpenAI text-embedding-3-small → phải đổi thành 1536 + rebuild schema.
- **pgvector >= 0.8.2** (CVE-2026-3172, CVSS 8.1). Image hiện dùng 0.8.2-pg16.
- **process_document() phải idempotent** — worker có thể retry tối đa 3 lần.
- **API không sync-call embedding** — mọi ingest đi qua queue. Không đảo ngược.
- **Forbidden:** hardcode API key, `SELECT *` trong production code, thay đổi DB schema mà không migrate.

## Domain

**RAG pipeline (ingest):**
1. `extract_text()` — PDF/TXT/MD → plain text
2. `chunk_text()` — chia theo token (chunk_size=800, overlap=100)
3. `embed()` — gọi embedding provider → vector float[1024]
4. Lưu vào `chunks` table với pgvector HNSW index

**RAG pipeline (query):**
1. Embed câu hỏi (`input_type='query'`)
2. Vector similarity search HNSW cosine distance, top-k=5
3. LLM generate với context chunks

**ARQ worker:**
- Task: `ingest_document(ctx, document_id, filename, content)`
- `process_document()` sync → chạy trong `run_in_executor` (tránh block event loop)
- On failure: cập nhật `status='failed'`, ARQ retry tối đa 3 lần

## MCP Servers (Day 2)

**5 servers cấu hình trong `.mcp.json`:**

| Server | Package / Command | Version | Role |
|---|---|---|---|
| filesystem | `@modelcontextprotocol/server-filesystem` | 2026.1.14 | Read/write project dir only |
| docker | `docker mcp gateway run` | Docker Desktop ≥ 4.40 | Container inspect + logs |
| kubernetes | `kubernetes-mcp-server` | 0.0.62 | K8s read-only (--read-only flag) |
| prometheus | `@wkronmiller/prometheus-mcp-server` | 2.0.0 | Query metrics (Day 4) |
| aws | `uvx awslabs.aws-api-mcp-server` | 1.3.38 | AWS read-only (IAM mcp-readonly) |

**Security:**
- K8s: ServiceAccount `mcp-readonly` + ClusterRole read-only → `infra/k8s/mcp-readonly/`
- AWS: IAM profile `mcp-readonly` với `ReadOnlyAccess` policy only
- Filesystem: allow-list chỉ project directory (không `/`, `$HOME`)
- Credentials qua env vars — KHÔNG hardcode trong `.mcp.json`

```bash
# Verify MCP
claude mcp list              # tất cả ✓ Connected
jq '.mcpServers | length' .mcp.json  # → 5
# Verify K8s least-privilege
kubectl auth can-i get pods --as=system:serviceaccount:insighthub:mcp-readonly    # yes
kubectl auth can-i delete pods --as=system:serviceaccount:insighthub:mcp-readonly # no ✓
```

## References

| Resource | URL/Path |
|---|---|
| Day 1 Lab Guide | `docs/lab-guides/Day1-AI-Coding-Agents.md` |
| Day 2 Lab Guide | `docs/lab-guides/Day2-MCP-Protocol.md` |
| Day 1 Spec | `Running-Project-Specification-Student.md` §5 |
| Day 2 Spec | `Running-Project-Specification-Student.md` §6 |
| Verify scripts | `scripts/verify-day-1.sh`, `scripts/verify-day-2.sh` |
| DB schema | `infra/db/init.sql` |
| K8s RBAC | `infra/k8s/mcp-readonly/` |
| ARQ docs | https://arq-docs.helpmanual.io |
| pgvector | https://github.com/pgvector/pgvector |
| MCP spec | https://modelcontextprotocol.io |
| AI prompt logs | `ai-prompts/day1.md`, `ai-prompts/day2.md` |
