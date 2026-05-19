# Day 2 - MCP Protocol Integration

Nguồn: mục 6 trong [Specification v3.3](../../Running-Project-Specification-Student.md), gồm đủ Must-have, Should-have, Nice-to-have, acceptance, submission, rubric và self-check.

## Đầu vào tích lũy
Day 1 đã có queue/worker. Chuẩn bị cluster lab local và Prometheus sample targets trước buổi; Day 3 sẽ triển khai chính thức, Day 4 mở rộng observability.

## Công việc phải hoàn thiện
Cấu hình đúng JSON/TOML của host đã chọn với4+ MCP backends Filesystem, Docker/container, Kubernetes, Prometheus; pin version/transport đúng host; Connected và Inspector/tools list/call từng server; ServiceAccount/RBAC read-only, filesystem allowlist; profile AWS scoped khi dùng AWS; debug 1 case thực và quiz 10 câu.

## Kiến thức và liên kết ngày sau
Host/client/server, Tools/Resources/Prompts, stdio/Streamable HTTP, schema/protocol và troubleshooting. K8s/Prometheus backend được tái sử dụng Day 4/5.

## Cách kiểm chứng
MCP mẫu trong tools/mcp là tài liệu tham khảo để học protocol/negative tests, không thay 4 tích hợp. Gateway phải thể hiện 4 backend được kiểm chứng. CLI hỗ trợ debug, không thay MCP task.

## Tổ chức thực hành
Prework đọc nguồn và chuẩn bị môi trường. Lab 50 phút dành cho demo, xử lý phần khó và review. Phần triển khai còn lại phải hoàn thiện sau buổi; không tự chuyển nhiệm vụ bắt buộc thành mở rộng. Mỗi ngày nộp prompt log, source/PR và evidence đúng phiên bản theo specification.

[Guide local/AWS](../Guide_Local_AWS_Cost_DO2603.md) áp dụng mọi lượt chạy. Bộ tests/fixture chỉ kiểm chứng phạm vi ghi nhận, không thay đầu ra dự án thật.

[Host guide](../Guide_Coding_Host_DO2603.md): status và calls thật trên từng backend; không bắt lệnh Claude trên Codex/Antigravity.
