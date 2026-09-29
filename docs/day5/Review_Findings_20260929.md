# Day 05 review - 29/09/2026

## Các lỗi đã tái hiện và sửa

| Phát hiện | Tác động | Sửa và kiểm chứng |
|---|---|---|
| Fallback Prometheus `or vector(0)` | Không có series vẫn có thể báo 0 lỗi | Chỉ suy ra zero từ traffic series có thật; missing/non-finite trả unknown |
| Scalar scientific notation | Bỏ sót giá trị như 1.2e-05 | Parse exponent, reject NaN/Inf/negative |
| Pod JSON sai dạng, Pending/init failure | Có thể báo healthy hoặc bỏ sót incident | Validate schema, kiểm Pending/initContainerStatuses, không báo lỗi Job Succeeded |
| Scale regex match một phần | `scale api to 2.5` bị hiểu thành 2 | Fullmatch lệnh mutation, deny lệnh ghép |
| Timeout kubectl | Child process còn chạy và không có reply rõ ràng | Kill/reap subprocess; trả outcome chưa xác minh, không retry mutation mù |
| Body HTTP không giới hạn trước read | Request lớn tiêu thụ bộ nhớ | Stream bounded 64 KiB, reject 413 |
| Healthcheck Docker chỉ đọc HTTP 200 | Bot not_ready vẫn healthy | Đọc boolean ready; readiness yêu cầu đủ cấu hình |
| Queue failure và malformed envelope | Thiếu regression coverage | 503 retriable, bounded enqueue, reject event ID/thread sai dạng |

10 regression cases thất bại trên code cũ; toàn bộ 34 tests hiện đạt (25 bot, 9 milestone). Có kiểm chứng chữ ký đúng tại biên ±300 giây và reject ±301 giây; tests không gửi Slack. Lượt live được ghi riêng.

## Phạm vi chủ đích

Bot local dùng env file 0600, không triển khai production Kubernetes. Production K8s, multi-step LLM, service catalog và interactive components là phần should/nice-to-have hoặc rubric L4, không được tự nhận đã hoàn thành. Destructive luôn deny; tier write chỉ scale đúng deployment sau approval. Không mở rộng quyền để thực thi destructive.

Worker hiện dùng một process cho lab, durable Redis inbox và reply cache. Không cam kết exactly-once giữa Slack, Redis, Kubernetes. Không khởi động nhiều worker trên cùng processing list. Optional AI summary không quyết định policy.

## Tham chiếu

- [Slack request verification](https://docs.slack.dev/authentication/verifying-requests-from-slack/): raw body HMAC, timestamp window.
- [Slack Events API](https://docs.slack.dev/apis/events-api/): ACK nhanh, retry/dedup.
