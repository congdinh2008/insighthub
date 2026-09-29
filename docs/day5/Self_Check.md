# Day 05 - self-check bàn giao

Cập nhật 29/09/2026. [Báo cáo E2E mới](../evidence/day5/20260929/Runtime_Validation.md), [review findings](Review_Findings_20260929.md), [PR #24](https://github.com/congdinh2008/insighthub/pull/24).

| Yêu cầu | Trạng thái | Bằng chứng |
|---|---|---|
| MH1-MH2 bot, HTTP endpoint | Đạt | Source đầy đủ, API/worker chạy thật, Docker build PASS |
| MH3 signature | Đạt | HTTPS live unsigned/expired/future reject 401, valid challenge 200; unit tests biên thời gian |
| MH4-MH5 tunnel/Slack App | Đạt trong lab | Request URL Verified, app_mention và reply qua Edge trong #chatops-test |
| MH6 ba intent | Đạt | Health, ingestion, pods trên Slack thật; thêm failing pod và missing Prometheus |
| MH7 hai MCP | Đạt | Audit có Kubernetes MCP và Prometheus MCP của lượt ngày 29/09 |
| MH8 audit | Đạt | JSON structured đã lọc; audit failure chặn mutation |
| MH9 policy/approval/scale | Đạt | Destructive deny; approval -> 2/2; replay/expiry deny; restore 1/1; identities riêng |
| MH10 tests/CI | Đạt | 34 tests, Ruff/Mypy, Docker build và hai job GitHub Actions success |
| MH11 screencast URL | Chưa đóng đủ | Đã tạo MP4 local khoảng 3 phút; URL Loom chờ quyền truy cập tài khoản |
| Regression UI | Một phần | API upload -> ready -> chat/citation trên Edge đạt; file chooser upload chờ quyền extension |

Verifier PASS với `scope=partial-runtime-contract`, `milestone_complete=false` đúng contract. Chưa tuyên bố đóng toàn bộ milestone khi URL Loom và UI upload còn pending. Không tự merge PR; PR dựa trên branch Day 04 vì main remote ở Day 03.
