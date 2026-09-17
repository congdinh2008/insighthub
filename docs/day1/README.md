# Day 01 - Solution: async ingestion với Redis/ARQ

Solution tham khảo cho bài **AI Coding Agent Refactor** của InsightHub DO2603. Học viên chuyển starter ba service, ingestion đồng bộ thành năm service với worker độc lập, bổ sung controlled retry và kiểm chứng bằng tests cùng browser E2E.

## Tài liệu và source

| Nội dung | Tài liệu |
|---|---|
| Yêu cầu và rubric | [Specification mục 5](../../Running-Project-Specification-Student.md) |
| Prompt sử dụng theo từng bước | [Bộ năm prompt](../../ai-prompts/day1.md) |
| Quy trình làm bài và commit | [Prompt workflow](../plans/Day01_Prompt_Workflow_v1.0.md) |
| Kế hoạch, bước làm, expected results | [Implementation plan](../plans/Day01_Implementation_Plan_v1.0.md) |
| Kiến trúc và quyết định kỹ thuật | [Architecture and decisions](Architecture_and_Decisions.md) |
| Chạy lab, tests, retry và recovery | [Runbook](Runbook.md) |
| Findings, requirements và self-check | [Review and self-check](Review_and_Self_Check.md) |
| Kết quả kiểm chứng tham khảo | [Execution report](../evidence/day1/Execution_Report.md), [Browser E2E](../evidence/day1/Browser_E2E_Report.md) |

## Các bước thực hiện

1. Bắt đầu từ starter `main`, đọc specification và dùng D1-P01 để xác định kiến trúc cùng invariants. Đối chiếu branch `day1-refactor` khi cần xem implementation tham khảo.
2. Dùng D1-P02 lập plan, review phạm vi và acceptance, tạo branch riêng cho bài Day 01.
3. Dùng D1-P03 triển khai API enqueue, Redis/ARQ, worker và retry endpoint; giữ layout/schema, sửa hai lỗi status recovery của starter trong commit riêng.
4. Dùng D1-P04 review code, kiểm thử input/error/concurrency/idempotency/lifecycle, chạy quality checks và đo latency.
5. Dùng D1-P05 nghiệm thu trên browser, ghi prompt logs, hoàn thiện evidence/self-check, commit và PR.

## Kết quả cần đạt

- `POST /documents` trả 202 sau queue acceptance; worker cập nhật cùng ID từ pending sang ready hoặc failed.
- Chat/retrieval giữ contract; vector validation, atomic chunks và idempotency được bảo toàn.
- `POST /documents/{id}/retry` chỉ xử lý failed document với đúng filename/hash/pipeline.
- Worker có ba retries 1s/2s/4s, JSON logs, health/metrics và graceful shutdown; tự restart khi mất kết nối Redis.
- Năm service chạy, backend/worker/live tests và Ruff/mypy/pre-commit đạt; có 11 browser cases và measurements.
- Bài nộp có AGENTS.md sáu section <=200 dòng, prompt log ít nhất ba lượt có giải thích và PR đúng convention.

Solution dùng fixture để kiểm chứng contract và pipeline local. Học viên chạy lại các bước theo [runbook](Runbook.md) và ghi kết quả cho môi trường của mình.
