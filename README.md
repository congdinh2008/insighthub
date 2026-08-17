# InsightHub

> **RAG Notebook** — running project cho module **AI-Native DevOps** (7 ngày).
> Học viên KHÔNG xây app từ đầu. App code được cung cấp sẵn. Nhiệm vụ của bạn:
> **DevOps-hóa** ứng dụng này — containerize, deploy, observe, secure, tối ưu cost.

InsightHub cho phép người dùng upload tài liệu (.txt/.md/.pdf) và hỏi đáp dựa
trên nội dung tài liệu đó (Retrieval-Augmented Generation).

---

## 🚀 Bắt đầu ở đây — Student Quick Links

| Tình huống | Đọc file này |
|---|---|
| **🆕 Lần đầu setup** | 👉 [`GETTING_STARTED.md`](./GETTING_STARTED.md) — onboarding 45-60' |
| **📅 Daily workflow** | [`docs/DAILY-WORKFLOW.md`](./docs/DAILY-WORKFLOW.md) — submit + grading flow |
| **🆘 Gặp lỗi** | [`docs/STUDENT-FAQ.md`](./docs/STUDENT-FAQ.md) — 30+ common issues + fix |
| **📖 Lab Day N** | [`docs/lab-guides/DayN-*.md`](./docs/lab-guides/) — workflow trong buổi |
| **📚 Pre-reading Day N** | [`docs/pre-reading/DayN-*.md`](./docs/pre-reading/) — đêm trước buổi học |
| **✅ Verify artifact** | `bash scripts/verify-day-N.sh` — auto-check artifact |

---

## Kiến trúc

### v0 (trạng thái khởi đầu — 3 service)

```
web (Next.js) → api (FastAPI, ingest ĐỒNG BỘ) → postgres (pgvector)
```

### v1 (sau refactor Day 1 — 5 service)

```
web → api → (enqueue) → redis → ingestion-worker → postgres (pgvector)
                ↓                                        ↑
                └──────── retrieval + LLM ───────────────┘
```

| Service | Tech | Vai trò |
|---|---|---|
| `web` | Next.js 15 (App Router, standalone) | Giao diện upload + chat |
| `api` | FastAPI + psycopg3 | API gateway, retrieval, LLM generation |
| `ingestion-worker` | Python + ARQ | Xử lý nền: chunk + embed (tách ra Day 1) |
| `redis` | Redis 7 | Job queue + cache (thêm Day 1) |
| `postgres` | PostgreSQL 16 + pgvector 0.8.2 | Metadata + vector store |

---

## Yêu cầu

Chạy `bash scripts/verify-setup.sh` để kiểm tra. Tóm tắt: Docker, Node.js 20+,
Python 3.11+, Git, kubectl, Helm, Terraform, AWS CLI, Claude Code.

---

## Chạy nhanh (v0)

```bash
# 1. Cấu hình biến môi trường
cp .env.example .env
#    (tùy chọn) điền ANTHROPIC_API_KEY + VOYAGE_API_KEY để có chất lượng thật.
#    Để trống vẫn chạy được — hệ thống dùng chế độ fallback.

# 2. Khởi động stack
docker compose up --build

# 3. Mở giao diện
#    Web:  http://localhost:3000
#    API:  http://localhost:8000/docs

# 4. Kiểm tra end-to-end
bash scripts/smoke-test.sh
```

### Provider mặc định: Gemini (free tier hào phóng)

InsightHub mặc định dùng **Google Gemini** (chat + embedding) — free tier đủ
chạy lab cả khoá. Đăng ký key 30 giây tại https://aistudio.google.com/apikey.

| Mode | LLM_PROVIDER | EMBEDDING_PROVIDER | Cần gì |
|---|---|---|---|
| **Gemini** (default) | `gemini` | `gemini` | 1 `GEMINI_API_KEY` (free) |
| Anthropic | `anthropic` | `voyage` hoặc `openai` | 2 keys |
| **Ollama** (on-prem) | `ollama` | `ollama` | Không cần key + GPU/RAM ≥16GB |
| Fallback (no key) | bất kỳ | `local` | Không cần gì (chất lượng thấp) |

**Khi không có key**:
- LLM trả lời extractive (trích đoạn đầu chunk).
- Embedding `local`: hash deterministic — pipeline chạy nhưng retrieval kém.
- Đủ cho smoke test, không đủ cho Day 7 showcase.

**Chạy với Ollama on-prem**:
```bash
docker compose --profile ollama up --build
# Sau khi container up, pull model (~9GB, 5-15 phút lần đầu):
docker compose exec ollama ollama pull deepseek-r1:14b
# Trong .env: LLM_PROVIDER=ollama, EMBEDDING_PROVIDER=ollama
```

Nhớ `EMBEDDING_DIM` khớp schema `VECTOR(n)` (default 1024). Gemini hỗ trợ
Matryoshka — code tự gửi `output_dimensionality=1024`. Ollama embedding
được truncate về 1024 trong code.

---

## Cấu trúc thư mục

```
insighthub/
├── web/                  # Next.js frontend (hoàn chỉnh)
├── api/                  # FastAPI gateway (hoàn chỉnh — ingest đồng bộ ở v0)
├── ingestion-worker/     # TRỐNG — học viên tách ra Day 1 (xem README bên trong)
├── infra/
│   └── db/init.sql       # Schema pgvector + HNSW index
├── infra/                # (Day 3) học viên thêm Terraform
├── observability/        # (Day 4) học viên thêm Prometheus/Grafana config
├── chatops-bot/          # (Day 5) học viên xây Slack bot
├── security/             # (Day 6) Promptfoo config
├── sample-docs/          # Tài liệu mẫu để test RAG (1 file chứa injection)
├── scripts/
│   ├── verify-setup.sh   # Kiểm tra môi trường pre-class
│   ├── smoke-test.sh     # Kiểm tra v0 end-to-end
│   └── verify-day-{1..7}.sh  # Verify artifact mỗi Day
├── docs/
│   ├── lab-guides/       # Workflow chi tiết mỗi Day
│   ├── pre-reading/      # Tài liệu đọc trước buổi
│   ├── STUDENT-FAQ.md    # 30+ common issues + fix
│   ├── DAILY-WORKFLOW.md # Submission + grading flow
│   └── reference-solutions/  # (trainer-only)
├── GETTING_STARTED.md    # 👉 Onboarding student — START HERE
├── docker-compose.yml    # v0 — 3 service
├── .env.example
├── .mcp.json.template    # (Day 2) cấu hình MCP servers
└── CLAUDE.md.template    # (Day 1) bộ nhớ dự án cho Claude Code
```

---

## Lộ trình 7 ngày — bạn sẽ làm gì với InsightHub

| Day | Chủ đề | Việc làm trên InsightHub |
|---|---|---|
| 1 | AI Coding Agents | Refactor: tách `ingestion-worker` + Redis. Viết `CLAUDE.md`. |
| 2 | MCP | Dockerize đủ 5 service. Cấu hình `.mcp.json` (4+ servers). |
| 3 | AI IaC + Pipeline | Sinh Terraform (EKS+RDS+ElastiCache) + CI/CD. Deploy lên K8s. |
| 4 | AIOps | Instrument Prometheus. Anomaly detection. AI RCA. |
| 5 | ChatOps | Xây Slack bot trả lời câu hỏi vận hành InsightHub. |
| 6 | Security + FinOps | Red-team (indirect injection). Guardrails. Cost dashboard. |
| 7 | Showcase | Demo InsightHub production-grade. |

---

## Lưu ý kỹ thuật

- **pgvector 0.8.2+** bắt buộc — phiên bản cũ dính CVE-2026-3172 (CVSS 8.1).
- **`EMBEDDING_DIM`** phải khớp `VECTOR(n)` trong `init.sql`. Đổi embedding
  model mà quên đổi schema là lỗi thường gặp nhất.
- File `api/app/services/ingestion.py` cố ý để ingest **đồng bộ** — đây là
  điểm refactor của Day 1, không phải bug.

---

*InsightHub v0.1.0 — tài liệu đào tạo nội bộ module AI-Native DevOps.*



# Tạo môi trường ảo có tên là 'venv'
python3 -m venv venv

# Kích hoạt môi trường ảo
source venv/bin/activate

# Sau khi kích hoạt, bạn có thể dùng pip bình thường
pip install -U pip
