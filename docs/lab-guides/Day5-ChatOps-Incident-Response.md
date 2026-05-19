# Day 5 - ChatOps Bot & Incident Response

Nguồn: mục 9 trong [Specification v3.3](../../Running-Project-Specification-Student.md), gồm đủ Must-have, Should-have, Nice-to-have, acceptance, submission, rubric và self-check.

## Đầu vào tích lũy
K8s/Prometheus MCP Day 2 và telemetry/anomaly/RCA Day 4 sẵn sàng.

## Công việc phải hoàn thiện
Hoàn thiện FastAPI/Slack SDK/MCP/audit; HTTP signature raw body/timestamp trước challenge; Slack App/scopes/connection LIVE; đủ3 intents health/ingestion hôm nay/pods lỗi;3-tier permissions và scale approval có identity riêng; tests và screencast 3 phút.

## Kiến thức và liên kết ngày sau
Events/ACK/handler/reply, bounded tool loop, audit, approval, RBAC. ACK<3s tách khỏi AI trả lời sau qua durable queue/dedup/retry.

## Cách kiểm chứng
Transport doubles dùng unit test, không thay Slack live. Socket Mode có thể bổ sung kết nối khi tránh public ingress; vẫn phải hoàn thành kiến thức/tests signature và chứng minh3 intents thật, tái sử dụng MCP Day 2.

## Tổ chức thực hành
Prework đọc nguồn và chuẩn bị môi trường. Lab 50 phút dành cho demo, xử lý phần khó và review. Phần triển khai còn lại phải hoàn thiện sau buổi; không tự chuyển nhiệm vụ bắt buộc thành mở rộng. Mỗi ngày nộp prompt log, source/PR và evidence đúng phiên bản theo specification.

[Guide local/AWS](../Guide_Local_AWS_Cost_DO2603.md) áp dụng mọi lượt chạy. Bộ tests/fixture chỉ kiểm chứng phạm vi ghi nhận, không thay đầu ra dự án thật.
