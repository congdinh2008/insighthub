# Day 02 - Execution report

Ngày kiểm thử: 22/09/2026, branch `day2-mcp`, base Day 01 `d676609`. Môi trường đã kiểm chứng: Docker Desktop macOS arm64, Codex CLI 0.154.0, MCP Inspector 2.7.0, Node 24.16.0 và năm backend MCP live.

## Kết quả

| Hạng mục | Kết quả thực tế |
|---|---|
| Cấu hình host | Codex, Claude Code và Antigravity đều parse PASS với 5 server; file local có mode `0600` |
| Codex host/model | 6 calls qua 5 server PASS, dùng model mặc định và approval chuẩn; [host trace](host-trace.json) |
| MCP live | 21 protocol/content/permission cases PASS; [probe](probe-all.json), [backend comparison](live-check.json) |
| Docker MCP Toolkit | Profile `insighthub-dev` có đúng 1 Filesystem server, image pin digest, mount `/project:ro`, network disabled và 3 tool đọc; [profile](toolkit-profile.json) |
| Kubernetes authorization | 3 quyền đọc trong namespace được phép; 6 quyền mutation/secret/cross-namespace bị từ chối bằng ServiceAccount `mcp-readonly` |
| Docker authorization | Tool chỉ nhận argv cố định; 4 API ngoài policy trả 403; output list/inspect bị projection; source Docker socket không cấp cho model |
| Debug và recovery | Host MCP đọc đúng `DAY2_CONFIG_MISSING`; operator recreate đúng `debug-case`; MCP xác nhận running và `DAY2_CONFIG_OK` |
| Browser E2E | 8/8 scenarios PASS qua Computer Use; 5 MCP, upload/chat và Prometheus UI đều có screenshot thật |
| Day 02 unit/quality | 14 unit tests PASS; Ruff lint và format PASS |
| Day 02 verifier | PASS partial runtime contract với backend live; `milestone_complete=false` theo thiết kế verifier |
| Day 01 regression | API 58 tests + 71 subtests, worker 10 tests, live contract 6 tests đều PASS |
| Verifier/MCP regression | 68 verifier tests, 22 MCP tests và 4 SDK negotiation modes đều PASS |
| Static quality | Ruff, mypy strict 22 source files và pre-commit đều PASS |

## Phạm vi Day 02

- Triển khai Filesystem, Docker operations, Kubernetes, Prometheus và InsightHub MCP bằng stdio.
- Pin binary, image và npm dependency; kiểm checksum release trước khi cài.
- Giới hạn quyền bằng source snapshot read-only, Docker policy proxy và Kubernetes RBAC.
- Tạo config project local cho Codex, Claude Code và Antigravity; không commit secret hoặc generated credential.
- Cung cấp prompt pack học viên, runbook, architecture/threat model, debug case, self-check, quiz practice và acceptance evidence.

Không thay đổi source nghiệp vụ hoặc triển khai chức năng Day 03 trở đi. MH1-MH9 có evidence. MH10 còn `PENDING` cho đến khi học viên có điểm quiz chính thức từ lớp; quiz practice không thay điểm này.

[Validation log](validation.txt) tổng hợp toàn bộ lệnh nghiệm thu. [Manifest](manifest.json) ghi source digest, config digest và hashes evidence cuối cùng.
