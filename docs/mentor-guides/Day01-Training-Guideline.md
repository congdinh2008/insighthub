# Training Guideline — Day 1: AI Coding Agents & Refactor InsightHub

> **Dành cho Mentor / Trainer**
> Module 7 — AI-Native DevOps · v1.0 · Tháng 5/2026
> Tác giả: Trần Mạnh Cong

---

## Tổng quan buổi học

| Thông số | Chi tiết |
|---|---|
| Thời lượng | 150 phút (2.5 giờ) |
| Mục tiêu chính | Học viên tự refactor InsightHub v0 → v1 bằng AI agent |
| Daily Artifact | `CLAUDE.md` + `ingestion-worker/` + `docker-compose` 5 service + 1 PR |
| Rubric Dimension | AI-Augmented Code Quality (12%) |
| Pass threshold | Level 3 ≥ 8/12 pts |

---

## Lịch trình chi tiết (150 phút)

| Thời điểm | Phân đoạn | Mode | Hoạt động |
|---|---|---|---|
| T+0 → T+15 | Kiểm tra chuẩn bị | **Trainer check** | Verify setup, Claude Code login |
| T+15 → T+30 | Recap & Hook | **Lecture** | Landscape AI agents, con số thị trường |
| T+30 → T+75 | Concept | **Lecture + Demo nhỏ** | Ba nhóm agent, CLAUDE.md, token efficiency |
| T+75 → T+90 | Best Practice | **Interactive** | Vòng lặp an toàn, Constraint-first prompt |
| T+90 → T+135 | **Live Demo + Hands-on** | **Lab** | Trainer demo 15', học viên làm 30' |
| T+135 → T+150 | Workshop | **Lab + Q&A** | Commit, push, tạo PR, hỗ trợ |

---

## T+0 — Kiểm tra chuẩn bị (15 phút)

**Trainer làm trước khi học viên vào:**
```bash
# Verify môi trường học viên (yêu cầu họ chạy)
bash scripts/verify-setup.sh     # PHẢI PASS toàn bộ
docker compose up --build        # 3 service (v0)
bash scripts/smoke-test.sh       # PASS 6/6
```

**Checklist đầu buổi (15 phút đầu):**
- [ ] Tất cả học viên có Claude Code chạy được (`claude --version`)
- [ ] API key Anthropic valid (có thể test `claude "say hi"`)
- [ ] InsightHub v0 chạy: `curl http://localhost:8000/healthz` → 200
- [ ] Git config đúng (`git config user.name`)

**⚠️ Nếu có học viên fail:** Cho họ ghép cặp với người setup xong, không để cả lớp chờ.

---

## T+15 — Recap & Hook (15 phút — Lecture Mode)

### Script cho Trainer

**Câu mở đầu (2 phút):**
> "Hôm nay các bạn sẽ không viết code refactor bằng tay. Các bạn sẽ chỉ huy một AI agent làm việc đó — và review nó như review một junior dev."

**Con số thị trường (3 phút):**
- Job posting yêu cầu AI agent skill: **+340%** (Jan 2025 → Jan 2026)
- Pure implementation role giảm **17%**
- Claude Opus 4.7: dẫn đầu SWE-bench Pro **64.3%** — giải được task thật

**Câu hỏi mở cho lớp (5 phút):**
> "Ai đã dùng Copilot/Cursor? Khác gì với việc 'AI agent tự refactor cả module'?"

**Key message (5 phút):**
- Copilot = autocomplete thông minh (IDE-first, per-line)
- Claude Code = agent tự đọc codebase, plan, thực thi nhiều file (CLI-first)
- DevOps engineer cần CLI-first vì sống trong terminal, cần scriptable cho CI/CD

---

## T+30 — Concept: AI Coding Agents Landscape (45 phút)

### Slide 1: Ba nhóm AI Coding Agent

| Nhóm | Đại diện | Khi nào dùng |
|---|---|---|
| **IDE-first** | Cursor, Windsurf | Sửa code lẻ, exploration |
| **CLI-first** | Claude Code, Aider | DevOps workflow, refactor lớn, CI/CD |
| **Cloud/async** | Devin, Codex Cloud | Task dài, song song nhiều task |

**Điểm nhấn cho lớp:** CLI-first là focus của khóa vì:
1. DevOps engineer sống trong terminal
2. Scriptable → đưa vào pipeline được (Day 3)
3. `CLAUDE.md` cho context bền vững giữa các phiên

### Slide 2: CLAUDE.md — "bộ nhớ dự án"

**Demo nhanh (5 phút):**
```bash
cat CLAUDE.md   # Cho học viên thấy file có gì
# Giải thích: AI đọc file này trước mỗi phiên → context
```

**6 section bắt buộc:**
1. **Architecture** — sơ đồ service, data flow
2. **Conventions** — code style, commit format
3. **Commands** — lệnh hay dùng
4. **Constraints** — ràng buộc không được vi phạm
5. **Domain** — kiến thức domain (RAG pipeline, embedding)
6. **References** — link đến tài liệu, spec

**Luật ≤ 200 dòng:** Dài quá → AI ignore phần giữa. Ngắn gọn = chính xác hơn.

### Slide 3: Token efficiency

Claude Code tiêu ít token hơn Cursor ~5.5x cho cùng task — quan trọng cho FinOps (Day 6).

---

## T+75 — Best Practice: Làm việc với AI Agent (15 phút)

### Vòng lặp an toàn

```
Prompt rõ ràng → Agent đề xuất → Human REVIEW → Approve → Agent thực thi → Verify
```

**Nhấn mạnh:** "Vibe-coding" (để agent tự làm không review) là anti-pattern vào production.

### Constraint-first Prompt (4 phần)

```
1. Context  — bối cảnh, file liên quan
2. Goal     — mục tiêu output
3. Constraint — ràng buộc, điều KHÔNG được làm
4. Plan gate — "trình bày PLAN trước khi sửa"
```

**Ví dụ KHÔNG tốt:**
> "Refactor ingestion sang async"

**Ví dụ TỐT:**
> "Đọc api/app/services/ingestion.py và api/app/routers/documents.py.
> Tách phần ingest thành ARQ worker.
> Ràng buộc: không đổi schema DB, không viết lại process_document(), dùng run_in_executor.
> Trình bày PLAN trước."

---

## T+90 — Live Demo + Hands-on (45 phút)

### Trainer demo (15 phút)

**Bước 0 (2 phút):** Khởi tạo CLAUDE.md
```bash
claude
# Trong phiên:
> /init
```

**Bước 1 (3 phút):** Prompt phân tích
```
Đọc api/app/services/ingestion.py.
Giải thích điểm yếu kiến trúc — chưa sửa gì.
```
→ Đọc to output cho cả lớp nghe. **Đây là điểm dạy "diagnose trước act".**

**Bước 2 (10 phút):** Prompt refactor (xem `ingestion-worker/README.md` để copy)
- Paste prompt, nhấn Enter
- Agent trả về PLAN → Dừng! Đọc PLAN to cho cả lớp
- Chỉ approve sau khi lớp review xong
- Agent thực thi → trainer chỉ xem, không can thiệp

> **Kỹ năng dạy:** Trainer nên để một bước bị fail (vd: quên REDIS_URL) để demo debug với AI.

### Học viên làm (30 phút)

**Hướng dẫn học viên:**
1. Mở terminal → `cd insighthub && claude`
2. Copy prompt từ `ingestion-worker/README.md`
3. Review PLAN agent đưa ra TRƯỚC khi approve
4. Sau khi implement: `docker compose up --build`
5. Verify: `bash scripts/verify-day-1.sh`

**Trainer circulate** (đi vòng hỗ trợ từng học viên):
- Ưu tiên học viên bị lỗi `event loop` (xem Troubleshooting)
- Không code giúp — gợi ý prompt tốt hơn

---

## T+135 — Workshop (15 phút)

**Học viên cần làm:**
- [ ] `git add -A && git commit -m "feat(ingestion): tách ingestion-worker + Redis queue"`
- [ ] `git push origin day1-refactor`
- [ ] Tạo PR trên GitHub với title `[Day 1] Refactor ingestion async + Redis queue`
- [ ] Copy link PR vào Slack `#day1-submissions`

**Trainer hỗ trợ:**
- Học viên nào chưa có GitHub remote → hướng dẫn `gh repo create`
- Q&A cuối buổi

---

## Troubleshooting — Lỗi thường gặp

| Triệu chứng | Nguyên nhân gốc | Cách fix cho học viên |
|---|---|---|
| `claude: command not found` | Chưa cài / Node < 20 | `npm install -g @anthropic-ai/claude-code` + `node -v` |
| API key invalid | Key hết hạn hoặc sai | Console Anthropic → regenerate → `claude login` |
| Worker không nhận job | API và worker trỏ khác REDIS_URL | Đảm bảo cả 2 dùng `redis://redis:6379` |
| `event loop is already running` | `process_document()` sync gọi trực tiếp trong async context | Bọc `loop.run_in_executor(None, process_document, ...)` |
| Upload vẫn trả 201 (không phải 202) | Chưa refactor `documents.py` | Kiểm tra `status_code=202` và không còn gọi `ingest_document_sync` |
| `docker compose build` fail ở worker | Build context sai | Dockerfile worker phải dùng `context: .` (root), không phải `./ingestion-worker` |
| `Module 'app' not found` trong worker | Không copy `api/app/` vào worker image | `COPY api/app ./app` trong Dockerfile |
| Agent loop mãi không xong | Prompt quá mơ hồ | Stop (`Ctrl+C`), rephrase với constraint-first |
| CLAUDE.md quá dài (>200 dòng) | Không follow template | Dùng table thay text prose, xóa comment thừa |

---

## Rubric Mapping — Chấm điểm nhanh

| Artifact | Verify command | L3 threshold | L4 threshold |
|---|---|---|---|
| CLAUDE.md | `wc -l CLAUDE.md` ≤ 200, `grep -c '^## '` ≥ 5 | 6 section đủ | Có forbidden patterns cụ thể |
| ingestion-worker/ | `ls ingestion-worker/` có Dockerfile + tasks.py | Tồn tại, build được | Có retry logic, structured log |
| docker-compose 5 service | `docker compose config --services \| wc -l` | = 5 | Health check đầy đủ |
| Async 202 | `curl -X POST /documents` → 202 in <1s | Đúng | <500ms |
| Worker ready | Poll 30s → status='ready' | Đúng | <15s |
| AI prompt log | `grep -c '^## Prompt' ai-prompts/day1.md` | ≥ 3 | ≥ 3 + giải thích "Why it worked" |
| Feature mới | Code review PR | Có 1 feature | Feature + tests |

**Scoring nhanh:**
- **L1 (0-3)**: Không refactor, không CLAUDE.md
- **L2 (4-7)**: Refactor bộ phận, CLAUDE.md thiếu section
- **L3 (8-9)**: Tất cả Must-have PASS + prompt log ≥ 3
- **L4 (10-12)**: L3 + retry logic + structured log + tests pass

---

## Lecture Mode vs Lab Mode

| Scenario | Điều chỉnh |
|---|---|
| **Lớp yếu** (junior majority) | Dành T+90 thêm 10' giải thích sync/async; Bước 5 (feature) để làm homework |
| **Lớp mạnh** (senior majority) | Thêm challenge: viết healthcheck cho worker; yêu cầu pre-commit hook |
| **Ít thời gian** | Rút Segment 2 còn 30', tập trung Hands-on; skip feature bước 5 |
| **Nhiều học viên fail setup** | Cho học viên ghép cặp; trainer demo live cả bước 0-3 |

---

## Key Teaching Points

1. **"Review như review junior"** — agent đưa PLAN, trainer/học viên PHẢI đọc và reject step thừa trước khi approve. Đây là skill quan trọng nhất Day 1.

2. **Constraint-first prompt** — học viên hay viết mơ hồ ("refactor this"). Trainer cần drill pattern: Context + Goal + Constraint + Plan gate.

3. **run_in_executor là bắt buộc** — `process_document()` sync dùng psycopg blocking. Trong ARQ async event loop mà gọi trực tiếp → block toàn bộ worker. Slide giải thích sync-trong-async cần sẵn.

4. **CLAUDE.md ≤ 200 dòng** — không phải văn học, là working doc. Agent đọc toàn bộ mỗi phiên.

5. **Day 1 là foundation cho Day 4** — không có queue (async worker), Day 4 không có `insighthub_ingestion_queue_depth` để observe. Nhắc lại mối liên hệ này.

---

## Đáp án tham khảo

> **Đáp án ở `docs/reference-solutions/`** — dùng để hỗ trợ học viên kẹt, KHÔNG phát trước buổi.
> Nếu học viên đang kẹt >10 phút, trainer có thể show đoạn code cụ thể (không toàn file).

**File cần tham chiếu:**
- `ingestion-worker/worker/tasks.py` — task `ingest_document` với `run_in_executor`
- `api/app/core/queue.py` — ARQ pool singleton
- `api/app/routers/documents.py` — enqueue + 202
- `docker-compose.yml` — redis + ingestion-worker service

---

## Homework cho học viên (chuẩn bị Day 2)

1. Hoàn tất refactor nếu chưa xong tại lớp
2. Đọc spec MCP overview tại modelcontextprotocol.io (~30 phút)
3. Tạo AWS IAM user `mcp-readonly` với policy `ReadOnlyAccess`
4. Setup kubeconfig context cho lab cluster (trainer cung cấp link)
5. Submit Day 1 artifact trước 23:59 qua `#day1-submissions`

---

*Trainer: cập nhật file này sau mỗi cohort — ghi lại lỗi mới gặp vào Troubleshooting.*
