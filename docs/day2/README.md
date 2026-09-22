# Day 02 - MCP Protocol Integration

Solution tham khảo DO2603, tiếp nối Day 01 trên branch `day2-mcp`. Bài tập dùng bốn backend bắt buộc và tái sử dụng MCP nội bộ InsightHub làm server thứ năm. Application vẫn giữ năm service mặc định.

| Đọc theo thứ tự | Nội dung |
|---|---|
| [Plan](../plans/Day02_Implementation_Plan_v1.0.md) | Scope, bước làm, expected outcomes và acceptance |
| [Architecture and Decisions](Architecture_and_Decisions.md) | Nguồn upstream, pin, trust boundaries và threat model |
| [Prompt pack](../../ai-prompts/day2.md) | Năm prompt mẫu: tìm hiểu, planning/review, triển khai, kiểm thử quyền, E2E/debug |
| [Docker MCP Toolkit](Docker_MCP_Toolkit.md) | Catalog/profile, nguồn upstream và cách dùng trong project thực tế |
| [Runbook](Runbook.md) | Dựng lab, kết nối host, Inspector, test và cleanup |
| [Debug case](../../debug-session-day2.md) | Crashed container, bằng chứng MCP, RCA, remediation và retest |
| [Review and Self-check](Review_and_Self_Check.md) | Mapping MH/SH/NH và bảy câu self-check |
| [Quiz and Answers](Quiz_and_Answers.md) | 10 câu luyện tập; không thay điểm quiz lớp |
| [Execution Report](../evidence/day2/Execution_Report.md) | Kết quả thực tế, traces và screenshots |
| [PR description](PR_Description.md) | Nội dung bàn giao để review branch |

MH10 chỉ được đánh dấu đạt khi học viên có điểm quiz chính thức >=7/10. Các kết quả kỹ thuật và bài luyện tập không tự tạo điểm quiz.
