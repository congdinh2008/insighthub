# [Day 2] Integrate MCP backends with read-only lab access

Day 01 đã có application async nhưng chưa có bốn tích hợp MCP thật để học viên đọc source, container, Kubernetes và metrics qua host. Branch này bổ sung Filesystem upstream, Docker Gateway chính chủ với catalog project tùy chỉnh, containers Kubernetes MCP và Prometheus MCP, đồng thời tái sử dụng hai tool read-only của InsightHub.

- Pin binary/npm/image; sinh config project Codex, Claude Code, Antigravity IDE và config Inspector, giữ secrets local.
- Lab opt-in gồm kind/SA RBAC, Prometheus scrape và Docker read proxy; base Compose vẫn năm service.
- Kiểm chứng host calls, Inspector/Computer Use, permission denial và case container thiếu env được phục hồi bởi operator.
- Cung cấp plan, 5 prompt mẫu học viên, runbook, architecture/threat model, self-check/quiz practice và evidence.

Config validation: ba host có năm server cùng launch definitions; 14 unit tests, Ruff và pre-commit pass. Codex discovery và live calls đủ năm server; Claude Code và Antigravity có static config validation theo đúng schema project.

Validation: xem [Execution Report](../evidence/day2/Execution_Report.md) và [requirement mapping](Review_and_Self_Check.md). Không thay source nghiệp vụ, schema hoặc assertions verifier. Không triển khai chức năng các day sau.

Review limits: Gateway 0.43.3 là prerelease đã kiểm thử trên Docker Desktop macOS arm64; Linux networking chưa được E2E. MH1-MH9 có evidence; MH10 còn thiếu điểm quiz chính thức.
