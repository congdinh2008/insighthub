# Day 1 — ingestion bất đồng bộ tối thiểu

```text
Upload → API kiểm tra file
       → transaction DB: tạo pending + hash/pipeline
       → ghi <document_id>.payload vào volume, fsync, commit DB
       → ARQ enqueue document:<document_id> vào Redis
       → HTTP 202 {id, status: pending}

Redis → ingestion-worker → đọc payload
                         → process_document(): khóa hàng → chunk → embed → store
                         → commit ready hoặc failed
                         → JSON ingestion_completed sau thành công
```

## Code và quyết định

- `api/app/routers/documents.py`: giữ kiểm tra extension, tên file, file rỗng,
  giới hạn đọc 10 MB và đóng UploadFile. Handler vẫn là `def` để FastAPI chạy
  công việc DB/file trong threadpool. `asyncio.run()` chạy riêng bước enqueue;
  tính bất đồng bộ của ingestion đến từ process worker riêng, không từ `async def`.
- `api/app/services/payloads.py`: tên file dựa trên ID do DB cấp, mở `xb` để
  không ghi đè. `fsync` file và thư mục trước commit; worker không thể nhận job
  trước khi file hoàn chỉnh và bản ghi hiển thị. `content_sha256` và `pipeline_id`
  ràng buộc payload/cấu hình ngay lúc nhận, dùng các cột có sẵn.
- `api/app/services/queue.py`: ARQ job chỉ mang document ID; `_job_id` cố định
  chống enqueue trùng khi job/result còn tồn tại. Enqueue có timeout 0,75 giây.
  Không retry mù khi mất phản hồi. `None` từ ARQ không được xem là tiếp nhận mới.
- `ingestion-worker/Dockerfile` và `ingestion-worker/worker.py`: Compose build worker
  từ Dockerfile riêng, chạy UID 1001. Wrapper alias `WorkerSettings` từ API vì ARQ
  cần class attribute trực tiếp, nên không sao chép pipeline.
- `api/app/worker.py`: `asyncio.to_thread()` tách pipeline đồng bộ khỏi event loop
  ARQ; `shield` và chờ thread khi bị hủy tránh bỏ chạy ngầm không được theo dõi.
  Tái sử dụng nguyên `process_document()` với row lock, hash, pipeline identity,
  savepoint và atomic chunks/metadata. Không sửa schema hoặc logic embedding.
- `docker-compose.yml`: API/worker dùng cùng YAML anchor môi trường, lock
  và lock dependencies. Volume `ingestion-payloads` cho API ghi, worker chỉ đọc.
  Thư mục thuộc UID 1001; Dockerfile tạo sẵn quyền 700, file payload quyền 600.
- `api/requirements.in` và `.txt`: thêm ARQ được pin; sinh lại lock có hash bằng
  uv. Docker vẫn cài với `pip --require-hashes`. Không nâng các package có sẵn.

## Hợp đồng lỗi

- Validation request lỗi: giữ 400/413/422 tương ứng, không enqueue.
- Ghi payload lỗi: rollback bản ghi admission, trả lỗi được API lọc; không enqueue.
- Enqueue lỗi/timeout không rõ kết quả: trả 503 với `detail.code=enqueue_unconfirmed`
  và `detail.document_id`. Không tự upload lại; kiểm tra GET `/documents` theo ID.
  File vẫn được giữ vì worker có thể đã nhận job.
- Chỉ đổi pending → failed khi lấy được khóa ngay (`FOR UPDATE SKIP LOCKED`).
  Không ghi đè ready/failed hoặc chờ worker đang khóa hàng; worker xử lý tiếp
  sẽ ghi trạng thái bằng transaction hiện có. Job tới muộn có thể đưa failed → ready.
- `POST /documents/{id}/retry`: chỉ nhận `failed`; khóa row, kiểm tra payload,
  SHA-256 và pipeline ID, đổi atomically sang pending rồi enqueue lại cùng job ID.
  Pending/ready là 409, thiếu ID là 404, payload mất/khác là 409. `keep_result=0`
  giải phóng job ID sau chạy. Không có automatic retry trong Day 1.
- Nội dung văn bản/PDF không hợp lệ hoặc provider lỗi được phát hiện trong worker:
  upload có thể đã trả 202, sau đó document thành failed với error_code. Test giữ
  assertion dữ liệu, retrieval và idempotency, chuyển kỳ vọng lỗi pipeline sang DB.
- Worker chỉ log ID, mã lỗi cố định, timestamp; không log toàn văn hay provider body.
  Event thành công có `event`, `document_id`, `timestamp` RFC3339 và `status=ready`.

## Kiểm tra

Chạy trong Ubuntu/WSL tại root repo:

```sh
docker compose config --quiet
docker compose up --build -d --wait
docker compose config --services
docker compose ps
make test-backend
python3 scripts/check_async_ingestion.py
python3 scripts/verify.py smoke
python3 -m unittest discover -s tests -p 'test_verify*.py' -v
```

`make test-backend` dùng schema test ngẫu nhiên, chỉ dọn dữ liệu của schema đó.
Các test route/DB dùng queue double và chạy worker rõ ràng sau phản hồi 202;
probe runtime kiểm tra HTTP/ARQ/worker thật, poll ID mới, chat với source mới và log
worker tương ứng. Probe dùng cố định 82 byte fixture; báo số byte/hash thực tế
trong `evidence/day1-async-runtime.json`, không xóa document/payload.

## Giới hạn của chặng này

- Retry thủ công không xử lý crash API sau commit `pending` trước enqueue. Giữ payload
  cho ready/failed; chưa tự dọn file. Lỗi admission có thể để orphan file cần đối soát.
- PostgreSQL và Redis không có transaction chung. API chết sau commit pending
  nhưng trước enqueue có thể để lại pending; chưa có outbox/reconciler cho crash đó.
  Nếu DB mất kết nối cả lúc ghi lỗi, log `failure_status_unconfirmed` cần đối soát.
- ARQ có thể replay khi process bị ngắt; idempotency bảo vệ chunks. Chưa thiết kế
  retry tự động riêng cho lỗi provider tạm thời, không tự retry lỗi dữ liệu.
- Chưa kiểm chứng crash/restart, Redis mất dữ liệu hoặc hàng đợi tồn quá hạn job
  mặc định của ARQ. AOF mỗi giây không bảo đảm không mất lần ghi gần nhất khi sập.
- Fixture không chứng minh chất lượng model thật hoặc tải lớn. Probe này không
  thay verifier Day 1, milestone tests, review cá nhân hay checklist nộp bài.

Khôi phục: review và bỏ riêng các thay đổi async trong code/Compose; giữ nguyên
volume, DB và payload. Không dùng `down -v`, reset Git hay migration schema.

## Kết quả thực tế ngày 2026-09-10

- Bản cuối: đủ năm service healthy; probe so sánh hash toàn bộ Settings của API
  và worker, khớp nhau; cả hai xác nhận fixture trước khi upload.
- Workload cố định 82 byte, SHA-256
  `8ae8bb488b7fc623831e0a4b6dfb6c90766b85afcc8208857700401271626e81`.
- Document ID 5: HTTP 202 trong 0,043713432 giây; poll đúng ID đạt ready với
  1 chunk trong 0,459079073 giây tính từ lúc bắt đầu upload. Chat HTTP 200,
  có source của file mới. Worker phát JSON thành công lúc
  `2026-09-10T09:07:08.522364+00:00`, đúng ID 5 và status ready.
- Hai ARQ replay độc lập cho ID 5 đều trả ready; so sánh cả chunk ID, thứ tự,
  nội dung, vector, embedding identity và metadata DB: không thay đổi. Payload
  giữ nguyên hash. Đây là kiểm tra job nội bộ, không tạo endpoint retry thủ công.
- `make test-backend`: 62/62 PASS, 3,756 giây, không skip. Các HTTP real-provider
  test có mock transport, không gọi dịch vụ trả phí.
- `python3 scripts/verify.py smoke --json`: PASS, upload 202, ID 4; không đồng nghĩa
  Day 1 hoàn tất. Probe bản cuối sau đó kiểm tra lại chat/health/202/ready bằng ID 5.
- Verifier regression: 66/68 PASS. Hai lỗi còn nguyên là
  `test_wrapper_missing_python_is_incomplete` và `test_wrappers_portable_outside_repo`;
  shell báo CRLF tại `verify-day-1.sh`/`verify-starter.sh`. Lượt đầu shell không nạp
  Node còn thêm hai lỗi PATH; chạy lại với Node có sẵn tại
  `/home/nhbduy/.nvm/versions/node/v22.23.2/bin` chỉ còn hai lỗi CRLF.
- Ruff PASS cho payloads.py, queue.py, worker.py, route documents.py và probe
  ingestion tại lần kiểm tra; bỏ riêng EXE002 do file mount Windows hiện executable.
  Lint toàn bộ các file cũ còn cảnh báo baseline, không tuyên bố toàn repo sạch.
- Mypy `--strict --follow-imports=silent`: PASS cho payloads.py, queue.py, worker.py;
  không phải chứng nhận strict toàn backend. Thêm annotation cho get_conn,
  initialize_database, close_pool và ServiceError.__init__ để hỗ trợ typing.
- `git diff --check`: PASS. Không đổi `infra/db/init.sql`, `process_document()` hay
  frontend. So sánh lock với HEAD chỉ thêm arq 0.28.0, redis 5.3.1, hiredis 3.4.1,
  pyjwt 2.13.0; các phiên bản cũ được giữ nguyên và Docker build kiểm tra hash.
- Prompt log chưa tổng hợp thêm, theo yêu cầu dành việc đó cho cuối bài.

Tham khảo API job ID, worker và healthcheck: [tài liệu ARQ](https://arq-docs.helpmanual.io/).
