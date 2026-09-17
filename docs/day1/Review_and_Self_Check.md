# Day 01 - Review solution và self-check

Dùng checklist này để review implementation tham khảo và đối chiếu bài làm. Kết quả kiểm thử nằm trong [Execution report](../evidence/day1/Execution_Report.md); quy trình AI-assisted development tại [bộ prompt Day 01](../../ai-prompts/day1.md).

## Findings và cách xử lý

| Finding | Rủi ro | Solution và kiểm chứng |
|---|---|---|
| Trả 202 trước queue acceptance | Accepted nhưng không có job | Enqueue trước response; 503 + failed metadata khi queue lỗi |
| Failed row xuất hiện trước ARQ xóa old finishing job | Retry nhận nhầm job cũ rồi pending | require_new=True; 409 giữ metadata, test finishing-job race |
| Mất phản hồi enqueue | Không biết Redis đã nhận job chưa | Initial upload tra job identity; manual retry ambiguous trả 503 và đọc lại status |
| Pipeline mismatch trước savepoint | Tài liệu còn pending sau lỗi terminal | Conditional fail_pending, không overwrite ready; DB integration test |
| Cancel coroutine không dừng sync thread | Đóng pool khi thread còn ghi DB | Shield + drain; cancellation unit test và SIGTERM runtime probe |
| Retry route thiếu upload protection | Oversized multipart đi qua parser | Middleware cover retry kể cả malformed ID; tests size/chunked input |
| Library logs chứa job arguments | Lộ document bytes/provider error | JSON allowlist và redaction tests |
| Redis outage làm ARQ loop thoát | Job mắc pending khi Redis đã phục hồi | Restart policy + safe process exit; fault injection giữ worker đang chạy, không start worker thủ công |
| Polling dừng sau một lỗi API | UI stale dù backend ready | Retry polling có giới hạn, tách lỗi poll/upload, manual refresh khởi động lại chu kỳ; browser E2E |
| Upload lỗi không refresh metadata | Failed document chưa xuất hiện trong danh sách | Refresh danh sách khi upload lỗi, giữ thông báo gốc; browser E2E |
| Mock provider ở API không tác động worker container | Test không kiểm đúng behavior | Tách isolated DB tests và live HTTP suite với worker thật |

## Đối chiếu requirements

| ID | Đầu ra trong solution | Học viên kiểm chứng |
|---|---|---|
| MH1, MH2 | AGENTS.md sáu section, <=200 dòng | Đọc context, đếm dòng và đối chiếu constraints với diff |
| MH3 | Worker Dockerfile, worker.py, requirements.txt | Build image và kiểm process |
| MH4, MH5 | Compose năm service với healthchecks | config --services và ps |
| MH6 | API upload async 202 | Đo năm lượt trên workload cố định, từng lượt <1s |
| MH7 | Worker xử lý cùng document ID | Poll ready <30s, kiểm chunks và correlated logs |
| MH8 | Chat/retrieval contract giữ nguyên | Tests answer/source/context/usage và browser chat |
| MH9 | Backend/worker/live suites và CI workflow | pytest -xvs có DB integration; kiểm CI run của bài nộp |
| MH10 | PR description và commit convention | Tạo PR đúng title trong repository bài làm |
| MH11 | Năm prompt hướng dẫn và mẫu ghi kết quả | Lưu ít nhất ba prompt đã dùng với giải thích/evidence |
| SH1 | Retry failed document cùng ID/file/pipeline | Positive/negative/concurrency tests và Swagger E2E |
| SH2 | Type hints toàn runtime API/worker | mypy --strict |
| SH3 | Ba retries exponential backoff | Assert 1/2/4s, nonretryable và exhaustion |
| SH4 | /healthz và /readyz trong worker | Probe loop, Redis heartbeat và DB |
| SH5 | JSON logs với ID/attempt/status | Parse actual events, kiểm redaction |
| SH6 | Forbidden patterns trong context | Kiểm schema, vectors, logging, tests và scope |
| NH1 | Worker /metrics | Counter/histogram từ jobs thật |
| NH2 | SIGTERM drain | Stop trong lúc xử lý; restart/redelivery không duplicate |
| NH3 | Ruff/mypy pre-commit hooks | Install và chạy hooks bằng locked tools |

Khi nộp bài, học viên gắn từng dòng với output của môi trường mình. Verifier chỉ kiểm một phần contract; các yêu cầu về prompt logs, PR, review và browser cần kiểm tra cùng artifacts tương ứng.

## Bảy câu self-check và đáp án tham khảo

1. **AGENTS.md có sáu section nào và forbidden patterns gì?** Architecture, Conventions, Commands, Constraints, Domain, References. Các pattern bị cấm gồm thay schema ngoài scope, pad/truncate vector, silent fallback, log payload/secret và bỏ assertions để làm test xanh.
2. **Constraint-first 4-part áp dụng thế nào?** Mỗi prompt bắt đầu bằng Ràng buộc, sau đó Mục tiêu, Tiêu chí chấp nhận, Tham chiếu. Ví dụ: giữ schema/layout, giới hạn web fixes ở status recovery, dùng Redis/ARQ, bảo toàn atomic/idempotent chunks và chỉ làm Day 01.
3. **Review plan trước implementation cần kiểm gì?** Kiểm đủ requirement mapping, file scope, 202/<1s/<30s, retry semantics, DB/queue boundary, meaningful tests và expected evidence. Yêu cầu sửa các bước vượt scope hoặc chưa có cách nghiệm thu, rồi mới triển khai.
4. **Dừng worker, API còn hoạt động không?** Có. Upload mới chờ ở pending trong queue; chat vẫn dùng tài liệu đã ready. E2E-02 và E2E-08 kiểm hành vi này, sau đó restore worker để xử lý job.
5. **Upload trong giới hạn và trên 10 MiB có kết quả gì?** Solution có measurements từng lượt trong execution report. Mẫu Markdown 1705 bytes có một warmup và năm lần đo riêng, mỗi lần cần trả 202 <1s và ready <30s. PDF đúng 10 MiB dùng metadata padding trả 202; file vượt 1 byte trả 413. Học viên đo lại trên môi trường mình và không suy rộng mẫu này thành mọi PDF.
6. **Ba prompt tiêu biểu và lý do?** D1-P02 khóa plan/acceptance trước code; D1-P03 triển khai một thay đổi chức năng có tests; D1-P04 tìm lỗi concurrency/lifecycle mà happy-path không phát hiện. D1-P01 và D1-P05 bổ sung architecture discovery và browser acceptance.
7. **Vì sao ARQ thay Celery?** Specification yêu cầu Redis/ARQ; ARQ đáp ứng queue, retry và lifecycle cho async Python trong bài. Shared sync pipeline chạy qua thread để giữ code hiện có. Day 01 chưa cần thêm broker hoặc workflow phức tạp.

## Invariants khi review diff

Giữ nguyên infra/db/init.sql. Web chỉ thay đổi polling recovery và refresh failed metadata, không đổi layout hoặc thêm feature. Kiểm vector finite/count/dimension/identity, row lock, rollback partial chunks, retry payload binding và delete semantics. Các thay đổi CI chỉ phục vụ kiểm thử Day 01; giới hạn DB/Redis non-atomic và recovery được mô tả tại [Architecture](Architecture_and_Decisions.md) và [Runbook](Runbook.md).
