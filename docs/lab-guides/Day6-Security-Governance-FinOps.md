# Day 6 - Security, Governance & FinOps

Nguồn: mục 10 trong [Specification v3.3](../../Running-Project-Specification-Student.md), gồm đủ Must-have, Should-have, Nice-to-have, acceptance, submission, rubric và self-check.

## Đầu vào tích lũy
InsightHub deployed/observed và Slack bot LIVE Day 1-5.

## Công việc phải hoàn thiện
Promptfoo 50+ cases theo coverage OWASP/direct/indirect/RAG poisoning/PII/excessive agency; initial/final reports và fix iterations; guardrails wrap LLM runtime; LiteLLM gateway route InsightHub/bot/coding workflow, 3 virtual keys/budgets; cost attribution/dashboard; AWS Budgets khi dùng AWS; threat model>=6 threats/mitigations.

## Kiến thức và liên kết ngày sau
OWASP LLM/Agentic, defense in depth, token economics/caching/routing, FinOps/budget enforcement. Những khối Promptfoo/guardrails/gateway vẫn bắt buộc.

## Cách kiểm chứng
Indirect injection phải upload/retrieve; chạy benign regression. Pin plugin ID theo catalog. Chứng minh blocked/allowed, route qua gateway, budget denial và giới hạn concurrent; không lấy config tồn tại làm bằng chứng. Cost tổng hợp các lượt lab, không chạy AWS liên tục.

## Tổ chức thực hành
Prework đọc nguồn và chuẩn bị môi trường. Lab 50 phút dành cho demo, xử lý phần khó và review. Phần triển khai còn lại phải hoàn thiện sau buổi; không tự chuyển nhiệm vụ bắt buộc thành mở rộng. Mỗi ngày nộp prompt log, source/PR và evidence đúng phiên bản theo specification.

[Guide local/AWS](../Guide_Local_AWS_Cost_DO2603.md) áp dụng mọi lượt chạy. Bộ tests/fixture chỉ kiểm chứng phạm vi ghi nhận, không thay đầu ra dự án thật.

Coding workload dùng host chính qua gateway nếu hỗ trợ; nếu không, học viên dùng chính host đó xây/chạy coding client/workflow API có context, diff, tests và gateway trace. Không cần cài host thứ hai. Cả ba keys cần workload thật và budget allowed/denied; quota subscription báo riêng. Xem [host guide](../Guide_Coding_Host_DO2603.md).
