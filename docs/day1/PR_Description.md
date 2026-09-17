# [Day 1] Refactor ingestion async + Redis queue

Upload trước đây giữ request đến khi ingestion hoàn tất và trả 201. Thay đổi này trả 202 sau validation/metadata/enqueue; ARQ worker xử lý chunk/embed/store qua Redis. Compose chạy năm service; DB schema và layout web giữ nguyên. Sửa polling recovery và refresh failed metadata của starter trong commit riêng.

Feature mới: POST /documents/{id}/retry nhận failed document với đúng filename/hash/pipeline và giữ nguyên ID. Worker có ba retries với backoff 1s/2s/4s, JSON logs, health/metrics, graceful shutdown và automatic restart khi Redis gián đoạn. Implementation giữ atomic/idempotent chunks và xử lý finishing-job race, ambiguous enqueue cùng deleted document.

## Validation

- 58 API tests + 71 subtests, 10 worker tests, 6 live HTTP tests và 68 verifier regression tests đạt trên local lab.
- Ruff, mypy strict 22 modules, pre-commit và starter MCP regression/smoke đạt.
- Browser E2E chạy 11 cases: upload ba định dạng, pending/ready, chat, input errors, worker independence, Swagger retry, Redis/API recovery và polling timeout. Redis outage được kiểm khi worker đang chạy, không start worker thủ công.
- Năm sample uploads đều <1s, ready <30s; file đúng 10 MiB được nhận, vượt 1 byte bị từ chối.
- Day 01 verifier đạt bounded runtime contract. GitHub CI được cấu hình trong starter workflow.

## Tài liệu review

- [Solution và hướng dẫn thực hành](README.md)
- [Năm prompt theo quy trình làm bài](../../ai-prompts/day1.md)
- [Code review và self-check](Review_and_Self_Check.md)
- [Execution report](../evidence/day1/Execution_Report.md) và [Browser E2E report](../evidence/day1/Browser_E2E_Report.md)

Validation dùng fixture local. DB commit và Redis enqueue không atomic; recovery runbook xử lý pending mất job trong phạm vi lab. Các số đo không đại diện chất lượng hoặc latency của real model.
