# Day 05 - Nghiệm thu ngày 29/09/2026

## Môi trường và nguồn

- Source implementation: `c1e07bf850004045703925d5d1982a4e1668d10b`, branch `day5-chatops-bot`.
- Cluster `kind-insighthub-local`, namespace `insighthub-dev`; bot local HTTP + Redis worker + Cloudflare Quick Tunnel.
- Microsoft Edge được điều khiển bằng Computer Use (`cua_repl`). Tin nhắn đều được nhập qua giao diện, không giả lập Slack bằng fixture.
- Workspace InsightHub DO 2603, kênh private `#chatops-test`, app `insighthub-do-2603`.
- [Thread nghiệm thu](https://insighthubdo2603.slack.com/archives/C0C3QBVE6AK/p1790662664155339).

## Kết quả live

| Case | Quan sát | Bằng chứng |
|---|---|---|
| Health | API ready, 0 pod lỗi, 5xx/5m=0; ba nguồn API/K8s MCP/Prometheus MCP | `edge-health.png`, `audit.json` |
| Ingestion trước upload | 0 tài liệu được tạo hôm nay theo ICT và đang ready; có mô tả giới hạn inventory | `edge-ingestion.png` |
| Ingestion sau upload | 1 tài liệu tạo hôm nay theo ICT và đang ready; đối chiếu ID 23 | `edge-ingestion-after-upload.png` |
| Pods bình thường | 6 pod không lỗi | `edge-pods.png` |
| Destructive | `delete namespace insighthub-dev` bị từ chối; namespace giữ nguyên | `edge-destructive-denied.png` |
| Scale approval | Yêu cầu 1 -> 2 chưa đổi replica, baseline 1/1 | `replicas-before-confirm.txt` |
| Confirm | Người duyệt trong đúng thread dùng token mới, API lên 2/2 | `replicas-after-confirm.txt`, `edge-scale-success.png` |
| Replay | Token đã dùng bị từ chối, không mutation thứ hai | `edge-replay-denied.png` |
| Restore | Token mới 2 -> 1, API về 1/1 | `replicas-restored.txt`, `edge-restore.png` |
| Expiry | Yêu cầu scale 1 -> 5 lúc 13:44:08, confirm lúc 13:45:33 ICT bị từ chối | `edge-expired-denied.png` |
| Pod lỗi thật | Pod test `day5-e2e-failed-20260929` exit 1; bot phát hiện `ready 0/1, Error`; pod test đã dọn | `edge-failed-pod.png` |
| Prometheus ngắt kết nối | Dừng port-forward của lượt test, bot trả unknown/partial; sau đó khôi phục port-forward | `edge-prometheus-unavailable.png` |
| Signature trên HTTPS thật | Unsigned 401; challenge đúng 200; chữ ký đúng nhưng timestamp -301/+301 giây đều 401; body >64 KiB 413 | `http-live-probes.json` |
| Regression API upload | Tài liệu tổng hợp `day5-edge-e2e.md`, ID 23, mode real, pending rồi ready trên Edge | `upload-api.json`, `edge-rag-chat.png`, `edge-rag-state.txt`; câu trả lời đúng CHATOPS-2909/60 giây, có citation, latency UI 2313 ms |

## Test và CI

- `pytest`: 34/34 (25 bot + 9 milestone), không skip/xfail.
- Ruff và Mypy bot: PASS. Pre-commit API/worker: PASS.
- Docker build: `insighthub-chatops:day5-review-20260929`, thành công.
- [Push CI](https://github.com/congdinh2008/insighthub/actions/runs/36532680278): `local-baseline` và `chatops-day5` đều success.
- [PR CI](https://github.com/congdinh2008/insighthub/actions/runs/36532825752): hai job đều success.
- Verifier: PASS, `runtime_verified=true`, 9 tests. Vẫn là `partial-runtime-contract`, không thay review specification.
- [PR #24](https://github.com/congdinh2008/insighthub/pull/24) là draft dựa trên `day4-observability`; remote main mới ở Day 03. Không merge hoặc chạy AWS apply.

## Video demo

[Video local khoảng 3 phút](Day05_Edge_Slack_Demo_3min.mp4), 179.93 giây, khoảng 4.8 MB. Ghi từ riêng tab Slack bằng Computer Use, lấy mẫu màn hình 1 lần/giây, ghép sáu đoạn 30 giây theo đúng thứ tự. Có cắt thời gian giữa các đoạn; không phải video ghi desktop liên tục. Không có voice-over. `demo-frame-manifest.json` lưu timestamp thật và SHA-256 từng frame.

1. 00:00-00:30: health ba nguồn.
2. 00:30-01:00: ingestion theo ngày ICT.
3. 01:00-01:30: pods qua Kubernetes MCP.
4. 01:30-02:00: scale 1 -> 2, confirm và replay deny.
5. 02:00-02:30: restore 2 -> 1 với approval mới.
6. 02:30-03:00: destructive deny và health cuối.

Token xuất hiện trong video đều đã được dùng/hết hạn, không chứa Slack signing secret, bot token, model key hoặc kubeconfig. Video chưa upload Loom: automatic approval review chặn truy cập tài khoản riêng khi chưa có ủy quyền cụ thể. Không tự coi MP4 local là đã nộp URL Loom.

## Giới hạn và phần chờ

- Upload qua file chooser của extension Edge bị chặn do chưa bật Allow access to file URLs. Đã yêu cầu người dùng bật quyền; upload API và kiểm tra UI được ghi tách biệt, không nhận là UI upload PASS.
- Không dùng evidence cũ để nhận là lượt chạy mới. Audit đã lọc, không có raw Slack payload hoặc credential.
- Quick Tunnel phụ thuộc process local, không phải production uptime. Bot model summary là tùy chọn và tắt trong lượt test này; RAG application vẫn dùng provider thật đang cấu hình.
- K8s production bot, multi-step LLM loop, service catalog và interactive components không nằm trong Must-have local Day 05.
