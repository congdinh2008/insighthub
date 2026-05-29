# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

InsightHub — RAG Notebook. Users upload documents (.txt/.md/.pdf), the system chunks + embeds them into pgvector, then answers questions via retrieval-augmented generation.

This is a **7-day AI-Native DevOps training project**. The app code is pre-built; students DevOps-ify it (containerize, deploy, observe, secure). Each day adds a layer — the codebase is intentionally incomplete in places students are expected to build.

## Architecture

### v0 (starting state — 3 services)
```
web (Next.js 15) → api (FastAPI, synchronous ingestion) → postgres (pgvector)
```

### v1 (after Day 1 refactor — 5 services)
```
web → api → redis (ARQ queue) → ingestion-worker → postgres (pgvector)
              ↓                                           ↑
              └──────── retrieval + LLM ─────────────────┘
```

| Service | Tech | Role |
|---|---|---|
| `web` | Next.js 15 (App Router, standalone) | Upload UI + chat interface |
| `api` | FastAPI + psycopg3 | API gateway, retrieval, LLM generation |
| `ingestion-worker` | Python + ARQ | Background: chunk + embed (built in Day 1) |
| `redis` | Redis 7 | ARQ job queue (added Day 1) |
| `postgres` | PostgreSQL 16 + pgvector 0.8.2 | Document metadata + vector store |

**API internal structure** (`api/app/`):
- `routers/`: `documents` (upload/list/delete), `chat` (RAG query), `health` (liveness/readiness)
- `services/`: `ingestion.py`, `embeddings.py`, `chunking.py`, `llm.py`, `retrieval.py`
- `core/`: `config.py` (pydantic-settings), `db.py` (psycopg3 pool), `metrics.py` (Prometheus counters/gauges)

## Commands

```bash
# Start v0 stack (3 services)
docker compose up --build

# # Start with local Ollama LLM (~9GB model, first pull takes 5-15 min)
# docker compose --profile ollama up --build
# docker compose exec ollama ollama pull deepseek-r1:14b

# End-to-end smoke test (run after stack is up)
bash scripts/smoke-test.sh

# Check environment prerequisites
bash scripts/verify-setup.sh

# Verify daily artifacts (N = 1..7)
bash scripts/verify-day-N.sh

# Tail service logs
docker compose logs -f api
docker compose logs -f web

# Access points
# Web UI:    http://localhost:3000
# API docs:  http://localhost:8000/docs
# Metrics:   http://localhost:8000/metrics
```

## LLM / Embedding Providers

Configured entirely via `.env` — no code changes needed to switch providers.

| Mode | `LLM_PROVIDER` | `EMBEDDING_PROVIDER` | Requires |
|---|---|---|---|
| **Gemini** (default) | `gemini` | `gemini` | `GEMINI_API_KEY` (free tier) |
| Anthropic | `anthropic` | `voyage` or `openai` | Two API keys |
| Ollama (on-prem) | `ollama` | `ollama` | No key, GPU/RAM ≥16GB |
| Fallback | any | `local` | Nothing (hash-based, poor retrieval) |

## Critical Constraints

- **`EMBEDDING_DIM` must match `VECTOR(n)` in `infra/db/init.sql`** (default 1024). Switching embedding models without updating the schema is the most common error. OpenAI `text-embedding-3-small` requires `VECTOR(1536)` and a schema rebuild.
- **pgvector >= 0.8.2 required** — older versions have CVE-2026-3172 (CVSS 8.1, buffer overflow in parallel HNSW index build).
- **`process_document()` in `api/app/services/ingestion.py` must remain idempotent** — the ARQ worker can retry jobs.
- **Synchronous ingestion in `api/app/services/ingestion.py` is an intentional architectural flaw** for Day 1 refactoring, not a bug to fix prematurely.
- CORS in `api/app/main.py` is set to `allow_origins=["*"]` intentionally — Day 6 tightens this for production.

## Day-by-Day Build Scope

| Day | What students build on top of v0 |
|---|---|
| 1 | Extract `ingestion-worker` + Redis queue; write `CLAUDE.md` |
| 2 | Dockerize all 5 services; configure `.mcp.json` (4+ MCP servers) |
| 3 | Terraform (EKS + RDS + ElastiCache) + GitHub Actions CI/CD; deploy to K8s |
| 4 | Prometheus instrumentation + anomaly detection + AI RCA |
| 5 | Slack ChatOps bot (`chatops-bot/`) with MCP backend |
| 6 | Promptfoo red-teaming (`security/`); LiteLLM gateway; cost dashboard |
| 7 | Production-grade demo |

## Skeleton / Placeholder Locations

- `ingestion-worker/worker/` — empty (`gitkeep`); students build the ARQ worker here in Day 1
- `chatops-bot/app/main.py` — skeleton with `TODO Day 5` comments; `handle_question()` raises `NotImplementedError`
- `observability/` — empty; students add Prometheus/Grafana config in Day 4
- `infra/` (beyond `db/init.sql`) — students add Terraform in Day 3
- `.mcp.json.template` — students configure in Day 2
