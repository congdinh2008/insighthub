# Day 1 AI Prompts — InsightHub Refactor

> Tài liệu chứng minh AI-augmented workflow.
> Mỗi prompt ghi rõ: context, constraint, lý do chọn cách tiếp cận, và điều chỉnh sau review.

---

## Prompt 1 — Phân tích điểm yếu kiến trúc v0

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-24 09:15

**Prompt**:
```
Đọc api/app/services/ingestion.py và api/app/routers/documents.py.
Chỉ phân tích — chưa sửa gì.
Liệt kê chính xác các điểm yếu kiến trúc của cách xử lý ingestion hiện tại
và giải thích hệ quả DevOps (observability, scalability, reliability).
```

**Agent output (tóm tắt)**:
- `ingest_document_sync()` chạy đồng bộ trong request handler → block worker process
- Không có queue → burst upload gây resource exhaustion
- Không retry → LLM API timeout 1 lần = mất tài liệu
- Status `pending` → `ready` không có bước trung gian (không observe được progress)
- Không có queue depth metric → Day 4 không có gì để alert

**Lý do prompt hoạt động**:
- Constraint-first: yêu cầu "chỉ phân tích" ngăn agent auto-edit
- Yêu cầu "hệ quả DevOps" hướng agent vào góc nhìn của khóa học, không chỉ code smell

**Điều chỉnh sau review**:
- Agent đề xuất thêm database transaction log — reject (out of scope Day 1)
- Giữ lại phần phân tích queue depth metric → áp dụng vào Prompt 2

---

## Prompt 2 — Refactor: tách ingestion-worker

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-24 09:45

**Prompt**:
```
Tách phần ingest đồng bộ thành một ARQ worker trong thư mục ingestion-worker/.

Ràng buộc (Constraint-first):
1. Worker dùng arq==0.26.3, kết nối Redis qua REDIS_URL env var
2. Tái sử dụng process_document() từ api/app/services/ingestion.py — KHÔNG viết lại logic chunk/embed
3. API enqueue job thay vì gọi trực tiếp, trả HTTP 202 ngay với status='pending'
4. process_document() là hàm sync — trong ARQ worker async phải dùng run_in_executor
5. Worker và API share cùng Python deps (api/requirements.txt đã có arq)
6. Giữ nguyên schema DB (không ALTER TABLE)
7. Thêm Gauge metric insighthub_ingestion_queue_depth

Trình bày PLAN chi tiết trước khi sửa file nào.
```

**Plan agent đưa ra (đã review)**:
1. Tạo `api/app/core/queue.py` — ARQ pool singleton
2. Tạo `ingestion-worker/worker/tasks.py` — `ingest_document()` async task
3. Tạo `ingestion-worker/worker/settings.py` — `WorkerSettings`
4. Sửa `api/app/routers/documents.py` — enqueue thay vì sync call, status_code=202
5. Sửa `api/app/main.py` — open/close ARQ pool trong lifespan
6. Tạo `ingestion-worker/Dockerfile` — context root, copy api/app + worker/
7. Sửa `docker-compose.yml` — thêm redis + ingestion-worker

**Review trước khi approve**:
- ✅ Plan step 1-7 hợp lý, đúng thứ tự
- ❌ Agent đề xuất dùng `pickle` serialize content cho ARQ — review: ARQ mặc định msgpack, bytes OK
- ✅ Giữ `run_in_executor` cho process_document()
- ❌ Agent muốn thêm async retry trong tasks.py — reject (ARQ đã có retry_jobs=True)

**Lý do prompt hoạt động**:
- Numbered constraints → agent không "sáng tạo" ngoài scope
- "Trình bày PLAN trước" tạo checkpoint review trước khi agent edit file thật

---

## Prompt 3 — Feature: hiển thị similarity score trong Chat UI

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-24 11:30

**Prompt**:
```
Thêm feature: chat UI hiển thị similarity score (%) bên cạnh tên file nguồn.

Context:
- ChatResponse từ api/app/routers/chat.py đã có trường contexts: list[dict]
  mỗi phần tử có {source, similarity, chunk_text}
- web/components/ChatPanel.tsx hiện chỉ hiển thị result.sources (list[str])
- API contract không thay đổi — chỉ update frontend

Yêu cầu:
1. Dedup sources theo filename (giữ similarity cao nhất)
2. Hiển thị dạng: "filename.pdf (similarity: 87.3%)"
3. Sort descending theo similarity
4. Tooltip giải thích ý nghĩa score (cosine distance)
5. Không thêm dependency mới
```

**Agent output**: Cập nhật `ChatPanel.tsx` đúng yêu cầu.

**Điều chỉnh sau review**:
- ✅ Dedup + sort logic chính xác
- ✅ Tooltip text hữu ích cho người dùng
- Thêm `Ctrl+Enter` shortcut để submit (agent đề xuất thêm, hữu ích → approve)

**Lý do prompt hoạt động**:
- Cite rõ API contract ("không thay đổi") → agent không refactor backend
- Constraint "không thêm dependency" → agent dùng vanilla JS, không import chart lib

---

## Prompt 4 — Auto-polling UploadPanel

**Tool**: Claude Code (claude-sonnet-4-6)
**Time**: 2026-05-24 11:55

**Prompt**:
```
UploadPanel.tsx: sau khi upload trả 202, document ở trạng thái 'pending'.
Hiện tại user phải reload để thấy status 'ready'.

Thêm auto-polling:
- Poll GET /api/documents mỗi 2 giây khi có bất kỳ document nào ở status='pending'
- Dừng poll khi không còn document 'pending'
- Hiển thị indicator "Worker đang xử lý — tự động cập nhật..."
- Dùng useEffect + setInterval + useRef (tránh closure stale state)
- Cleanup interval khi component unmount
```

**Agent output**: Cập nhật `UploadPanel.tsx` với polling logic đúng.

**Điều chỉnh sau review**:
- ✅ `useRef` cho interval ID tránh re-render loop
- ✅ Cleanup trong return của useEffect
- Sửa: agent dùng `docs` directly trong setInterval callback → stale closure. Fix: dùng `setDocs` callback form để đọc current state
