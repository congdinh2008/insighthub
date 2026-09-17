# Day 01 - Bộ prompt thực hiện solution

Sử dụng lần lượt năm prompt để hoàn thiện bài **AI Coding Agent Refactor** của InsightHub. Mỗi prompt tạo một đầu ra để học viên kiểm tra trước khi chuyển bước: kiến trúc, plan, implementation, kiểm thử và nghiệm thu. Yêu cầu chi tiết tại [Specification mục 5](../Running-Project-Specification-Student.md).

| Prompt | Đầu vào | Đầu ra cần review |
|---|---|---|
| D1-P01 | Starter và specification | Architecture map, constraints, AGENTS.md |
| D1-P02 | Kết quả phân tích | Plan, phạm vi file, acceptance và review thiết kế |
| D1-P03 | Plan đã được học viên duyệt | Async ingestion, controlled retry và tests chức năng |
| D1-P04 | Diff implementation | Findings đã xử lý, tests và quality checks |
| D1-P05 | Stack đã qua kiểm thử | Browser E2E, evidence, self-check, commits và PR |

Đọc [solution guide](../docs/day1/README.md) và [quy trình sử dụng prompt](../docs/plans/Day01_Prompt_Workflow_v1.0.md) trước khi bắt đầu. Các prompt dùng cấu trúc **Ràng buộc -> Mục tiêu -> Tiêu chí chấp nhận -> Tham chiếu**.

## D1-P01 - Tìm hiểu kiến trúc và hoàn thiện context

```text
RÀNG BUỘC
Đọc AGENTS.md và specification trước. Chỉ phân tích source, chưa sửa
ứng dụng hoặc cài dependency. Chỉ đề xuất thay đổi thuộc Day 01.
Giữ DB schema, layout/frontend features, error contract và embedding invariants.
Phân biệt lỗi starter với phần cần triển khai Day 01.

MỤC TIÊU
Phân tích InsightHub starter: trách nhiệm web/API/PostgreSQL, luồng
upload/chunk/embed/store/chat, điểm ingestion đồng bộ gây blocking.
Đề xuất nội dung AGENTS.md đủ sáu section, không quá 200 dòng.

TIÊU CHÍ CHẤP NHẬN
Trình bày architecture map; API contracts; trạng thái tài liệu;
atomicity/idempotency và vector identity phải giữ; tests hiện có.
Chỉ ra chức năng đã có để không tính nhầm là feature mới.
Context gồm Architecture, Conventions, Commands, Constraints,
Domain, References; có forbidden patterns cụ thể.
Dẫn file nguồn cho từng nhận định và liệt kê câu hỏi cần làm rõ.

THAM CHIẾU
Running-Project-Specification-Student.md mục 2 và 5;
api/app/routers/documents.py; api/app/services/ingestion.py;
api/app/core/index.py; infra/db/init.sql; api/tests/; web/components/.
```

**Vì sao cần:** Có source map và constraints trước khi giao refactor, tránh thay đổi sai contract hoặc làm lại chức năng có sẵn.

**Học viên review:** Upload starter trả 201 sau xử lý; DB chỉ có pending/ready/failed; web đã polling và có citations. Kiểm tra context bằng file source, không chỉ dựa vào lời giải thích của agent.

**Đối chiếu solution:** [Architecture và quyết định](../docs/day1/Architecture_and_Decisions.md), [AGENTS.md](../AGENTS.md).

## D1-P02 - Lập kế hoạch và review thiết kế

```text
RÀNG BUỘC
Chưa triển khai code. Bám specification Day 01 và kiến trúc đã đọc.
Không đổi schema/layout hoặc thêm chức năng của Day 02-07.
Web chỉ sửa polling recovery và cập nhật metadata failed sau upload lỗi.
Chọn Redis/ARQ và dùng lại process_document, không copy pipeline.

MỤC TIÊU
Lập plan chuyển ingestion sang worker độc lập trên day1-refactor.
Chọn feature mới: retry failed document bằng đúng file gốc,
giữ nguyên document ID. Tự review thiết kế trước khi trình plan.

TIÊU CHÍ CHẤP NHẬN
Map 11 Must-have, 6 Should-have, 3 Nice-to-have sang bước làm,
file thay đổi, kết quả dự kiến và cách kiểm chứng.
Chốt payload/job ID, transaction boundary, trạng thái/lỗi,
retry 1s/2s/4s, health/logs/metrics và graceful shutdown.
Có baseline, tests lỗi/concurrency/idempotency, workload latency,
11 browser E2E cases, kế hoạch commit và tiêu chí hoàn thành.
Nêu rủi ro DB commit/Redis enqueue và cách recovery trong scope.
Dừng ở plan để tôi review trước khi triển khai.

THAM CHIẾU
Specification mục 4, 5.3-5.9; scripts/VERIFICATION_CONTRACT.md;
process_document và ServiceError; API tests và Compose hiện có.
```

**Vì sao cần:** Chốt các quyết định có ảnh hưởng đến dữ liệu và nghiệm thu trước khi code. Review nằm trong lượt planning, học viên quyết định chấp nhận hoặc yêu cầu chỉnh plan.

**Học viên review:** Có đúng năm service; 202 chỉ sau queue acceptance; manual retry chỉ cho failed đúng filename/hash/pipeline; giữ assertions và không mở rộng schema.

**Đối chiếu solution:** [Kế hoạch triển khai](../docs/plans/Day01_Implementation_Plan_v1.0.md).

## D1-P03 - Triển khai async ingestion và controlled retry

```text
RÀNG BUỘC
Thực hiện plan tôi đã duyệt trên branch day1-refactor.
Giữ schema/layout, chỉ sửa hai lỗi trạng thái web trong plan.
Giữ các assertions validation, vectors,
atomicity/idempotency. Không thêm service ngoài năm thành phần.
Không log payload/secret; không fallback real provider sang fixture.

MỤC TIÊU
Ghi baseline rồi triển khai Redis/ARQ và ingestion-worker.
API validate file, ghi metadata, enqueue và trả 202; worker gọi
pipeline dùng chung qua thread để không chặn ARQ event loop.
Thêm POST /documents/{id}/retry nhận lại file của failed document.

TIÊU CHÍ CHẤP NHẬN
Compose chạy web, api, postgres, redis và ingestion-worker.
Ready có chunks; lỗi provider cập nhật failed với safe error code.
Retry giữ cùng ID, đúng filename/hash/pipeline; 409 cho trạng thái
hoặc payload không hợp lệ, 404 cho ID thiếu, 503 khi queue lỗi.
Transient provider errors có tối đa ba retries, backoff 1s/2s/4s.
Worker có JSON logs, health/metrics, graceful shutdown và restart policy.
Khi Redis hoạt động lại, worker tự phục hồi; không cần start thủ công.
Thêm tests chức năng cùng implementation và cập nhật sync tests
sang 202 + chờ đúng ID, giữ assertions dữ liệu/chat đã có.

THAM CHIẾU
Plan đã duyệt; api/app/services/ingestion.py; core/errors.py;
core/upload_limit.py; api/tests/test_integration.py; docker-compose.yml.
```

**Vì sao cần:** Tập trung một thay đổi chức năng hoàn chỉnh: upload được nhận nhanh, xử lý nền và retry có kiểm soát.

**Học viên review:** API không embed trong request; worker dùng shared pipeline; payload có giới hạn; job identity và row lock chống duplicate; lỗi enqueue không trả 202 giả.

**Đối chiếu solution:** [API documents](../api/app/routers/documents.py), [queue adapter](../api/app/services/queue.py), [worker](../ingestion-worker/worker.py).

## D1-P04 - Review code và kiểm thử

```text
RÀNG BUỘC
Review diff Day 01 theo specification và plan. Chỉ sửa findings
trong scope. Không xóa assertions, skip DB tests hoặc blanket-ignore
mypy để đạt PASS. Test trên Compose project và database lab riêng.

MỤC TIÊU
Review correctness của queue/DB/retry/lifecycle, bổ sung test còn
thiếu và chạy đầy đủ backend, worker, live HTTP, regression và
quality checks. Mỗi finding cần có ảnh hưởng, cách sửa và evidence.

TIÊU CHÍ CHẤP NHẬN
Kiểm invalid/empty/oversized input, provider failure/exhaustion,
Redis unavailable/ambiguous response, concurrent manual retry,
old finishing job, deleted document, vector và pipeline mismatch.
Chứng minh không partial/duplicate chunks hoặc overwrite ready.
Kiểm SIGTERM khi đang có job, redelivery và Redis persistence.
Ngắt Redis khi worker đang chạy, chỉ start lại Redis: worker phải tự
phục hồi và xử lý retry cùng ID; không dùng start worker để làm test xanh.
pytest -xvs chạy DB tests; Ruff, mypy --strict và pre-commit đạt.
Đo một warm-up rồi năm upload mẫu, từng lượt 202 <1s, ready <30s.
Báo kết quả từng suite, findings đã sửa và giới hạn kỹ thuật còn lại.

THAM CHIẾU
api/tests/; ingestion-worker/tests/; tests/milestones/day1/;
Makefile; pyproject.toml; .pre-commit-config.yaml; CI baseline.
```

**Vì sao cần:** Happy-path upload không phát hiện race giữa metadata và vòng đời job. Lượt review riêng giúp học viên kiểm tra chất lượng code AI sinh.

**Học viên review:** DB tests thực sự chạy; mocks chỉ dùng trong đúng process; live tests có Redis/worker thật; retry backoff có assertions; logs không chứa dữ liệu tài liệu.

**Đối chiếu solution:** [Code review và self-check](../docs/day1/Review_and_Self_Check.md), [test reports](../docs/evidence/day1/Execution_Report.md).

## D1-P05 - Browser E2E và hoàn thiện bài nộp

```text
RÀNG BUỘC
Dùng Computer Use & Control Browser trên lab đã qua tests.
Upload bằng file picker và retry bằng Swagger UI; không dùng API
script thay thao tác browser. Fault injection chỉ trên project lab.
Chỉ ghi kết quả đã quan sát và không commit secrets/raw private data.

MỤC TIÊU
Chạy nghiệm thu UI, đối chiếu toàn bộ yêu cầu Day 01 và chuẩn bị
bài nộp gồm code, prompt log, evidence, self-check, commits và PR.

TIÊU CHÍ CHẤP NHẬN
Kiểm upload .md/.txt/.pdf, pending -> ready, chat/sources và reload.
Kiểm empty/invalid/oversized file; worker dừng nhưng chat vẫn chạy.
Redis lỗi tạo failed và tự cập nhật danh sách; chỉ phục hồi Redis,
worker tự restart, retry cùng ID thành ready. Kiểm API outage khi
polling, tự xóa lỗi kết nối sau recovery; timeout/refresh hoạt động đúng.
Swagger thể hiện 202, 409 và 404 đúng trường hợp.
Lưu ảnh, ID, mode, thời gian và expected/actual cho 11 cases.
Đối chiếu MH/SH/NH, trả lời bảy self-check; ghi ít nhất ba prompt
đã dùng kèm Why it worked, What I changed và evidence.
Chia commit theo thay đổi hoàn chỉnh; PR title đúng specification.
Kiểm tra CI, lưu bài nộp và dừng lab khi kết thúc.

THAM CHIẾU
Specification 4.3-4.4, 5.4-5.9; plan E2E-01 đến E2E-11;
scripts/verify-day-1.sh; docs/day1/Runbook.md; browser evidence.
```

**Vì sao cần:** Kiểm chứng luồng học viên nhìn thấy và đóng gói kết quả để người khác có thể review, chạy lại.

**Học viên review:** Đúng file/ID, ảnh phản ánh trạng thái thật, fixtures có nhãn; PR chứa thay đổi Day 01, validation và giới hạn kỹ thuật.

**Đối chiếu solution:** [Browser E2E report](../docs/evidence/day1/Browser_E2E_Report.md), [runbook](../docs/day1/Runbook.md), [PR description](../docs/day1/PR_Description.md).

## Ghi kết quả sau mỗi prompt

Khi thực hành, học viên lưu prompt đã dùng và điền record sau để hoàn thiện MH11:

```markdown
### D1-Pxx - Tên công việc
- Host / version / model / auth mode:
- Time:
- Context / commit:
- Prompt đã dùng:
- Kết quả:
- Why it worked:
- What I changed sau review:
- Evidence: diff, test output hoặc screenshot
```
