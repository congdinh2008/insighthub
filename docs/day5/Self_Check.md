# Day 05 - self-check bàn giao

| Yêu cầu | Trạng thái | Bằng chứng |
|---|---|---|
| MH1-MH3 bot, HTTP endpoint, signature | Đạt | `chatops-bot/app/`, bot suite 4/4, milestone suite 6/6; signature sai bị 401 |
| MH4-MH5 cloudflared/Slack App | Đạt trong lab | Quick Tunnel vào cổng bot, Event Request URL đã Verified, `app_mention` và reply thật trong `#chatops-test` |
| MH6 ba intent | Đạt | [Slack live](../evidence/day5/Runtime_Validation.md): health, ingestion theo ngày tạo/ready, pods lỗi |
| MH7 hai MCP | Đạt | Audit event `Ev0C410A4H9T`, `Ev0C49LCCARJ`, `Ev0C3QKDQ8MV` ghi Kubernetes MCP và Prometheus MCP |
| MH8 audit | Đạt | [Audit JSON đã lọc](../evidence/day5/audit.json), runtime JSONL ngoài Git |
| MH9 policy/approval/scale | Đạt | Deny destructive, approval trước scale, confirm đúng người/thread, replay deny, restore 1/1; ServiceAccount đọc/ghi tách biệt |
| MH10 tests/CI | Cục bộ đạt; remote pending | Bot 4/4, milestone 6/6, Ruff/Mypy, Docker build và verifier PASS. CI job đã thêm nhưng chưa có remote run |
| MH11 screencast | Pending theo chỉ đạo trainer | Trainer chọn để video 3 phút sau; capture sai foreground đã xóa |
| Regression | Đạt | Smoke upload -> ready -> chat/citation/metrics PASS với tài liệu ID 22 |

**Giới hạn của kết quả:** verifier báo `scope=partial-runtime-contract`, `milestone_complete=false` theo đúng contract, không tự coi đó là nghiệm thu mọi tiêu chí. `0 doc` ở lượt Slack ingestion là snapshot trước smoke upload; không phải first-completion count. Quick Tunnel tạm thời và phụ thuộc local process. Remote CI/PR pending do credential `gh` hết hạn và remote `main` chưa có Day 04. Không dùng fixture làm evidence Slack.
