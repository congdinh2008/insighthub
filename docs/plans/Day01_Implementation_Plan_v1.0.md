# Day 01 - Kế hoạch triển khai solution

Mục tiêu: chuyển InsightHub starter từ ingestion đồng bộ sang Redis/ARQ và worker độc lập, hoàn thiện toàn bộ yêu cầu Day 01. Nguồn yêu cầu: [Specification v3.3 mục 4 và 5](../../Running-Project-Specification-Student.md). Branch thực hành: `day1-refactor`; điểm xuất phát: starter `main`.

## 1. Phạm vi và thiết kế

| Thành phần | Starter | Solution Day 01 |
|---|---|---|
| Runtime | web, api, postgres | Thêm redis và ingestion-worker, tổng năm service mặc định |
| Upload | Request gọi ingestion sync, trả 201 sau xử lý | Validate + metadata + enqueue, trả 202 |
| Processing | Trong API request | Worker gọi shared process_document qua thread |
| Trạng thái | pending/ready/failed | Giữ nguyên, web polling theo ID |
| Feature mới | Chưa có manual retry | Retry failed document với đúng file, giữ nguyên ID |
| Chất lượng | Baseline tests của starter | Bổ sung async/retry/lifecycle tests, strict typing, hooks và CI checks |

Luồng xử lý:

```text
Web -> POST /documents -> validate + metadata -> Redis/ARQ -> 202
                                                   |
                                            ingestion-worker
                                                   |
                                       chunk -> embed -> store
                                                   |
                                           PostgreSQL/pgvector

Web polling -> GET /documents -> pending | ready | failed
Web chat -> POST /chat -> retrieval + generation + sources
Swagger -> POST /documents/{id}/retry -> cùng queue/worker
```

Các ràng buộc xuyên suốt:

- Giữ DB schema, layout/tính năng frontend, API response fields và error contract ngoài thay đổi async đã định nghĩa. Chỉ sửa hai lỗi starter liên quan trạng thái: polling sau lỗi API và cập nhật metadata failed sau upload lỗi.
- Giữ vector finite/count/dimension/identity, atomic chunks, row locks và idempotency.
- Một shared pipeline; không dùng BackgroundTasks thay queue hoặc copy business logic vào worker.
- Chỉ Day 01; không thêm IaC, cloud deployment, MCP integrations, dashboards, bot hoặc gateway của các day sau.
- Fixture có nhãn; real provider không fallback sang fixture. Secrets qua env, không log payload/provider body.
- Payload file bounded 10 MiB, Redis nội bộ có AOF/volume; không thêm storage service hoặc bảng outbox.

## 2. Requirement-to-evidence mapping

| ID | Công việc triển khai | Kết quả dự kiến / cách kiểm chứng |
|---|---|---|
| MH1 | Hoàn thiện AGENTS.md theo host đã chọn | Đủ Architecture, Conventions, Commands, Constraints, Domain, References; diff tuân thủ context |
| MH2 | Context ngắn gọn | <=200 dòng, không nhân bản qua adapter |
| MH3 | Worker độc lập | Có Dockerfile, worker.py, requirements.txt và process chạy thật |
| MH4 | Compose năm service | config --services đúng web/api/postgres/redis/ingestion-worker; Ollama chỉ optional profile |
| MH5 | Startup và healthchecks | Năm service Running/healthy |
| MH6 | Upload async | 202 <1s trên workload local cố định; không embed trong request |
| MH7 | Worker ingestion | Cùng document ID ready <30s, chunk_count >0, correlated log |
| MH8 | Chat regression | 200, answer/sources/contexts/usage đúng contract |
| MH9 | Preserve và bổ sung tests | pytest -xvs pass, DB tests chạy thật, CI output tương ứng commit |
| MH10 | Branch và PR | PR title `[Day 1] Refactor ingestion async + Redis queue` |
| MH11 | Prompt logs | Ít nhất ba prompt đã sử dụng, có context, metadata, Why it worked, What I changed và evidence |
| SH1 | Feature controlled retry | Positive, invalid state/payload, missing ID và concurrency tests |
| SH2 | Type hints | mypy --strict toàn runtime API và worker |
| SH3 | Automatic retries | Initial attempt + tối đa ba retries, backoff 1s/2s/4s |
| SH4 | Worker health endpoint | /healthz và /readyz trong worker process; readiness kiểm DB và Redis heartbeat |
| SH5 | Structured logging | JSON events với ID/attempt/status, không chứa payload hoặc secrets |
| SH6 | Forbidden patterns | AGENTS ghi rõ giới hạn schema, vectors, logging, tests và scope |
| NH1 | Worker metrics | /metrics có counter/histogram từ job thật |
| NH2 | Graceful shutdown | SIGTERM khi có job, drain và exit đúng; restart/redelivery không duplicate |
| NH3 | Pre-commit | Ruff và mypy chạy bằng locked tooling |

Learning outcomes: chọn một coding host và ghi version/model/auth; kiểm chứng read/approval/deny trên dữ liệu lab; dùng constraint-first 4 phần, agentic loop, code review và trả lời bảy câu self-check.

## 3. Contract cần chốt trước implementation

| Tình huống | Expected result |
|---|---|
| Upload hợp lệ, queue nhận job | 202, ID mới, pending, chunk_count=0 |
| Extension không hỗ trợ | 400 |
| Tên/file/text/PDF không hợp lệ | 422; bảo toàn failed metadata của baseline khi đã tạo document |
| File >10 MiB | 413 trước multipart processing vượt giới hạn, bao phủ cả retry route |
| Provider lỗi sau enqueue | 202 đã được nhận; worker retry hoặc chuyển failed với safe error_code |
| Queue lỗi xác định | 503, không trả accepted giả; metadata failed có thể retry |
| Redis mất kết nối khi worker đang chạy | Worker tự restart, phục hồi khi Redis sẵn sàng; không cần start worker thủ công |
| UI mất kết nối API khi pending | Tiếp tục polling có giới hạn; xóa lỗi kết nối khi phục hồi; refresh thủ công bắt đầu chu kỳ mới |
| Manual retry failed đúng filename/hash/pipeline | 202 cùng ID, không tạo document mới |
| Retry pending/ready/mismatch hoặc old job còn finishing | 409, không thay dữ liệu ngoài yêu cầu |
| Retry ID thiếu | 404 |
| Hai retry đồng thời hoặc job redelivery | Không duplicate chunks; không overwrite kết quả ready |

Transient provider timeout/network/429/5xx được retry; input/vector/identity lỗi không retry. DB và Redis không có transaction chung: cần kiểm tra ambiguous enqueue và runbook cho pending mất job. Thiết kế chi tiết tại [Architecture and decisions](../day1/Architecture_and_Decisions.md).

## 4. Các bước thực hiện

| Bước | Input và công việc | Output / điều kiện chuyển bước |
|---|---|---|
| 1. Architecture/context | D1-P01; đọc spec/source/tests, chọn host, kiểm tra ba tầng quyền với fixture lab | Architecture map, context sáu section, constraints có dẫn source |
| 2. Planning/review | D1-P02; chốt queue/state/retry/errors, file scope, tests và commit strategy | Học viên review plan trước implementation |
| 3. Baseline | Tạo branch; project/ports riêng; chạy starter tests/smoke, ghi version và source hash | Baseline để so sánh, không dùng dữ liệu lab khác |
| 4. Async ingestion | D1-P03; dependencies, Redis, worker image, queue adapter và API 202 | Shared pipeline chạy trong worker, five-service stack |
| 5. Retry/worker quality | Retry API cùng ID, backoff, JSON logs, health/metrics, SIGTERM | Tests state/payload/concurrency; safe outcomes và lifecycle |
| 6. Code review/tests | D1-P04; review diff, sửa findings, chạy unit/DB/live suites và strict checks | Test reports; không skip DB tests hoặc giảm assertions |
| 7. Runtime/E2E | Đo latency, lifecycle, restart; D1-P05 thao tác web/Swagger | Measurements, 11 browser cases và screenshots |
| 8. Bài nộp | Logs, self-check, evidence hashes, commits, PR và CI | Checklist Day 01 có nguồn kiểm chứng; dừng lab giữ dữ liệu |

## 5. Phạm vi file và commit

| Nhóm | File chính |
|---|---|
| API/queue | api/app/routers/documents.py; services/queue.py; services/ingestion.py; core/config.py, errors.py, providers.py, upload_limit.py |
| Typing | Runtime modules dưới api/app và ingestion-worker/worker.py |
| Worker/build | ingestion-worker/; docker-compose.yml; .env.example; hash lockfiles; .dockerignore |
| Tests/quality | api/tests/; ingestion-worker/tests/; tests/milestones/day1/; Makefile; pyproject.toml; pre-commit; CI baseline |
| Starter fixes | web/components/UploadPanel.tsx: polling recovery, refresh failed metadata; không đổi layout |
| Tài liệu | AGENTS.md; ai-prompts/day1.md; docs/plans/; docs/day1/; README; GETTING_STARTED |
| Evidence | docs/evidence/day1/; evidence/day1.json |

Ba commit review chính của solution:

1. `fix(web): recover document status after request failures`: sửa hai lỗi trạng thái của starter; có thể cherry-pick riêng.
2. `feat(ingestion): add resilient async worker and controlled retries`: API, queue/worker, dependency/config, tests và CI; bao gồm automatic recovery khi Redis gián đoạn.
3. `docs(day1): add student solution and verified acceptance evidence`: context, plan, năm prompt hướng dẫn, runbook, self-check và kết quả kiểm thử cuối.

Mỗi commit phải có mục đích kỹ thuật rõ, không đưa secret hoặc raw private logs vào Git. PR mô tả behavior trước/sau, validation và giới hạn kỹ thuật; xem [PR description](../day1/PR_Description.md).

## 6. Kế hoạch kiểm thử

| Nhóm | Cases | Pass khi |
|---|---|---|
| Baseline/regression | Upload/chat/retrieval/source/usage/delete, verifier và MCP starter | Giữ các assertions, chỉ chuyển contract sync sang async đúng thiết kế |
| Input | .md/.txt/.pdf; empty/whitespace/invalid PDF; size boundary; malformed retry ID | Đúng 400/413/422, không ready giả hoặc bypass upload limit |
| API/queue | 202, failed enqueue, ambiguous response, retry old finishing job | Trạng thái metadata và queue acceptance nhất quán trong contract |
| Data | Vector count/dimension/finite/identity; atomicity; duplicate delivery | Không partial chunks, không trộn embedding space hoặc duplicate indices |
| Retry | 1/2/4s, transient/terminal/exhaustion; manual concurrent/mismatch | Attempt/status/error_code đúng; cùng ID và không overwrite ready |
| Lifecycle | Worker stop/start, SIGTERM đang xử lý, Redis outage khi worker còn chạy, AOF persistence, delete pending | Worker tự phục hồi khi Redis hoạt động lại, API/chat độc lập, không duplicate chunks |
| UI recovery | API gián đoạn khi polling, upload failed, 60 lần polling và manual refresh | Tự hồi phục, giữ lỗi upload, danh sách đúng; timeout có hướng dẫn và refresh khởi động lại polling |
| Quality | Ruff format/check, mypy strict, pre-commit, CI | Scope công bố đạt, không blanket ignores hoặc skipped required tests |

Database integration dùng schema lab riêng. Provider mock trong test process không tác động worker container; live suite phải chạy qua HTTP + Redis + worker thật. Milestone suite có sáu scenarios: refactor_regression, empty_input, duplicate_or_invalid, async_upload, worker_ingests, retry_idempotent.

Đo latency với sample-docs/so-tay-van-hanh.md: ghi bytes/hash/mode/chunk config, một warm-up riêng rồi năm uploads. Mỗi lượt phải 202 <1s, ready <30s; lưu đúng ID và tất cả số đo. Thử PDF text nhỏ và file sát giới hạn riêng, không suy rộng performance từ một sample.

## 7. Computer Use & Control Browser E2E

| Case | Thao tác | Expected result |
|---|---|---|
| E2E-01 | Upload Markdown bằng file picker | Đúng file ready và chunk_count >0 |
| E2E-02 | Stop worker, upload, start worker | UI pending rồi tự polling ready |
| E2E-03 | Hỏi nội dung tài liệu | Answer/source đúng contract, fixture có nhãn |
| E2E-04 | Upload TXT/PDF rồi reload | Cả hai ready, trạng thái giữ sau reload |
| E2E-05 | Oversized, empty, invalid PDF | UI lỗi rõ, không báo ready giả |
| E2E-06 | Redis down khi worker đang chạy gây failed; chỉ restore Redis; Swagger retry file gốc | Worker tự restart; 202 cùng ID rồi ready, không start worker thủ công |
| E2E-07 | Swagger retry ready/missing ID hoặc wrong payload | 409/404, dữ liệu không bị sửa sai |
| E2E-08 | Chat trong khi worker stopped | Chat còn hoạt động; restore stack sau phép thử |
| E2E-09 | Pending, API down rồi up | Polling thử lại và tự chuyển ready, xóa lỗi kết nối |
| E2E-10 | Upload PDF hỏng/queue unavailable khi không có pending | Document failed tự xuất hiện, giữ thông báo upload lỗi |
| E2E-11 | Worker dừng quá 60 lần polling; refresh rồi start worker | UI báo dừng polling, refresh bắt đầu chu kỳ mới và tự cập nhật ready |

Ghi URL, timestamp, mode, file/hash, document ID, expected/actual và screenshot. Browser chứng minh luồng người dùng; HTTP measurements dùng đo latency. Kịch bản và ảnh tham khảo tại [Browser E2E report](../evidence/day1/Browser_E2E_Report.md).

## 8. Hoàn thiện và nộp bài

- Chạy lệnh nghiệm thu theo [Runbook](../day1/Runbook.md); kiểm logs, tests và source scope.
- Lưu ít nhất ba prompt đã dùng theo mẫu tại [prompt pack](../../ai-prompts/day1.md), kèm quyết định review và evidence.
- Đối chiếu [requirements và bảy self-check](../day1/Review_and_Self_Check.md).
- Tạo evidence envelope gắn source/artifact hashes; chạy verifier trong hạn freshness quy định.
- Commit theo Conventional Commits, tạo PR đúng title, kiểm CI và nộp artifacts theo specification.
- Dừng project lab khi kết thúc, giữ dữ liệu cần review; không tác động project khác.
