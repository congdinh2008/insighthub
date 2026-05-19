# Day 1 - AI Coding Agent Refactor

Nguồn: mục 5 trong [Specification v3.3](../../Running-Project-Specification-Student.md), gồm đủ Must-have, Should-have, Nice-to-have, acceptance, submission, rubric và self-check.

## Đầu vào tích lũy
Starter sync/3 service chạy được.

## Công việc phải hoàn thiện
Chọn một coding host (Claude Code/ChatGPT-Codex/Antigravity), hoàn thiện AGENTS.md 6 sections <=200 dòng và adapter/bằng chứng context được áp dụng; dùng agent đọc code/constraint-first prompt; tách ingestion-worker + Redis/ARQ để đủ 5 thành phần; upload202, worker xử lý nền, status ready/failed và chat giữ đúng contract; tests/PR/prompt log>=3 có review cá nhân; cải tiến nhỏ thực sự mới theo rubric.

## Kiến thức và liên kết ngày sau
Async/refactor, agentic loop, permissions, code review, test/idempotency. Worker là bắt buộc để Day 4 đo backlog.

## Cách kiểm chứng
5 service local;202/<1s và ready/30s trên fixture workload cố định; tests async/retry/chat. Không coi refactor nhỏ còn sync là hoàn thành.

## Tổ chức thực hành
Prework đọc nguồn và chuẩn bị môi trường. Lab 50 phút dành cho demo, xử lý phần khó và review. Phần triển khai còn lại phải hoàn thiện sau buổi; không tự chuyển nhiệm vụ bắt buộc thành mở rộng. Mỗi ngày nộp prompt log, source/PR và evidence đúng phiên bản theo specification.

[Guide local/AWS](../Guide_Local_AWS_Cost_DO2603.md) áp dụng mọi lượt chạy. Bộ tests/fixture chỉ kiểm chứng phạm vi ghi nhận, không thay đầu ra dự án thật.

Baseline chạy bằng `make test-backend`. Khi refactor, cập nhật test sync 201 thành async 202 + worker completion, giữ các kiểm tra dữ liệu/idempotency/provider. Nếu chạy pytest trên host, dùng Python 3.12, cài dependency API và verifier từ requirements đã khóa, rồi chạy `PYTHONPATH=api pytest api/tests/ -xvs`; integration cần PostgreSQL lab riêng và RUN_DB_TESTS=1. Không diễn giải việc đổi contract có chủ đích thành quyền xóa test.

[Setup một host](../Guide_Coding_Host_DO2603.md), cùng yêu cầu/rubric cho ba lựa chọn.
