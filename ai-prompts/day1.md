# Day 1 — Nhật ký prompt cho refactor AI-augmented

**Host/model:** Codex desktop trên Windows PowerShell; GPT-6 (session identity), không có thông tin build/version chính xác.

Nhật ký này được đối chiếu với `AGENTS.md`, các thay đổi tại `ingestion-worker/`, `api/app/routers/documents.py`, `api/app/services/ingestion.py`, `api/app/core/queue.py` và các kiểm thử Day 1. Không lưu secret, API key hay giá trị cấu hình cục bộ.

## Prompt 1 — Hoàn thiện context cho coding agent

**Mục tiêu:** Đọc cấu trúc InsightHub và hoàn thiện `AGENTS.md` thành context dùng cho Day 1, để coding agent hiểu luồng web → API → Redis/ARQ → ingestion-worker → PostgreSQL.

**Ràng buộc:** Giữ tối đa 200 dòng; có đúng sáu phần Architecture, Conventions, Commands, Constraints, Domain và References; không đưa secret, API key hoặc nội dung tài liệu riêng tư vào context; không thay đổi schema hay source code ứng dụng khi chỉ đang xây dựng context.

**Tiêu chí thành công:** `AGENTS.md` nêu rõ upload bất đồng bộ trả 202, worker dùng pipeline dùng chung, retry 1/2/4 giây với tối đa ba lần chạy lại sau lần đầu, và các bất biến về idempotency, vector 1024 chiều cùng trạng thái `pending`/`ready`/`failed`.

**Ngữ cảnh tham chiếu:** `README.md`, `Running-Project-Specification-Student.md`, `docs/Guide_Coding_Host_DO2603.md`, `api/app/`, `infra/db/init.sql` và các tests hiện có.

### Why it worked

Prompt giới hạn đầu ra vào các bất biến có thể kiểm tra trong code và rubric. Các ràng buộc đặt trước yêu cầu viết giúp context không biến thành bản tóm tắt chung chung và không vô tình đưa cấu hình nhạy cảm vào repository.

### What I changed

Tôi giữ sáu phần theo hướng dẫn host và bổ sung các contract cần thiết cho refactor: queue bền vững, HTTP 202, retry, idempotency, giới hạn embedding và cách chạy các kiểm thử. Tôi loại bỏ mọi giá trị từ `.env` và không coi context là bằng chứng thay cho test chạy thực tế.

## Prompt 2 — Khởi tạo ingestion worker ARQ

**Mục tiêu:** Tạo `ingestion-worker/worker.py` và các tệp Docker/requirements cần thiết để ARQ lấy document ID từ Redis, xử lý ingestion nền và cập nhật document sang `ready` hoặc `failed`.

**Ràng buộc:** Không thay DB schema; không dùng `BackgroundTasks` hay xử lý in-process thay queue; worker phải gọi lại pipeline atomic dùng chung ở `api/app/services/ingestion.py` trong threadpool thay vì sao chép nghiệp vụ; retry sau lần chạy đầu tối đa ba lần với backoff 1/2/4 giây; log chỉ metadata an toàn và có event JSON `ingestion_completed`, `document_id`, `status`, timestamp RFC3339.

**Tiêu chí thành công:** Docker Compose có năm service mặc định gồm `ingestion-worker`; worker nhận document ID đã enqueue, giữ `pending` trong khi retry, chỉ ghi `ready` khi chunks/metadata commit hoàn toàn, và ghi `failed` với error code khi hết retry hoặc tài liệu không hợp lệ.

**Ngữ cảnh tham chiếu:** `api/app/services/ingestion.py`, `api/app/core/config.py`, `api/app/core/db.py`, `docker-compose.yml`, `ingestion-worker/README.md`, `api/tests/test_unit_worker.py` và `api/tests/test_integration.py`.

### Why it worked

Prompt xác định rõ điểm tích hợp và những điều không được thay thế, nên agent tái sử dụng transaction, row lock, savepoint và kiểm tra vector đã có thay vì tạo một pipeline thứ hai. Tiêu chí log và trạng thái giúp kết quả có thể xác minh từ container đang chạy.

### What I changed

Tôi review để worker chuyển phần blocking sang thread, dùng cùng `Settings`/pipeline với API, và chỉ log document ID cùng mã lỗi an toàn. Tôi giữ nguyên schema và xác nhận retry không cho lỗi cũ ghi đè một lần retry thành công.

## Prompt 3 — Refactor upload bất đồng bộ và kiểm thử retry

**Mục tiêu:** Refactor `POST /documents` để tạo document `pending`, enqueue document ID vào Redis/ARQ và trả HTTP 202 nhanh; cập nhật tests cho việc poll `GET /documents` đến `ready` hoặc `failed`.

**Ràng buộc:** Giữ validation hiện có: extension sai 400, file quá 10 MiB 413 và file rỗng 422; enqueue thất bại phải trả 503 với code `queue_unavailable`; không xóa hoặc nới assertion để làm test xanh; cùng document ID/payload/pipeline sau khi thành công phải no-op, còn filename/payload/pipeline khác phải trả 409 `document_conflict`; không ảnh hưởng retrieval/chat của document `ready` đúng embedding identity.

**Tiêu chí thành công:** Endpoint trả 202 sau khi enqueue bền vững, không chạy extraction/embedding trên request thread; worker hoàn tất tài liệu fixture trong thời hạn local; test bao phủ enqueue, compensation khi queue lỗi, retry/idempotency và chat sau khi document `ready`; `git diff --check` sạch.

**Ngữ cảnh tham chiếu:** `api/app/routers/documents.py`, `api/app/core/queue.py`, `api/app/core/errors.py`, `api/app/services/ingestion.py`, `api/tests/test_unit_http.py`, `api/tests/test_unit_queue.py`, `api/tests/test_integration.py` và `docs/lab-guides/Day1-AI-Coding-Agents.md`.

### Why it worked

Prompt nêu đủ contract HTTP, điều kiện lỗi và bất biến dữ liệu trước khi yêu cầu refactor. Điều đó buộc review tập trung vào compensation giữa DB/Redis và tính đúng đắn của retry, thay vì chỉ đổi mã trạng thái từ 201 sang 202.

### What I changed

Tôi chấp nhận enqueue qua `core/queue.py` và thêm xử lý compensation an toàn khi queue/DB gặp lỗi, vẫn phát lại `QueueUnavailable` theo public contract. Tôi cập nhật tests cho contract async, giữ validation cũ, và chỉ ghi nhận kết quả fixture đã đo: upload 202, poll đúng document ID đến `ready`, chat trả contexts, cùng event `ingestion_completed`; tôi không diễn giải chúng là chất lượng RAG thực-provider hay hoàn thành toàn bộ milestone.

## Kết quả kiểm tra được ghi nhận trong Day 1

- `python -m pytest api/tests/ -xvs -p no:cacheprovider` trong Docker test environment: 64 tests passed, 68 subtests passed.
- `docker compose config --quiet` và `docker compose up --build -d --wait`: passed.
- Fixture smoke: upload trả 202 trong 0.019601 giây; document `2` thành `ready` sau 0.1024 giây, có một chunk; chat trả 200 với contexts.
- Log worker có `ingestion_completed`, `document_id=2`, `status=ready` và timestamp RFC3339.
- `git diff --check`: passed.

Chưa ghi nhận Ruff, mypy strict hoặc full Day 1 milestone gate là đã chạy/pass.
