# Day 05 - Runbook ChatOps local

## Mục tiêu và phạm vi

Nghiệm thu app Slack `A0C3EU2GD35` trong workspace `T0C35P86Z1D`, kênh private `#chatops-test` (`C0C3QBVE6AK`). Bot xử lý ba intent đọc và scale duy nhất deployment `insighthub-api` trong namespace `insighthub-dev` khi user `U0C3ETL1LKD` xác nhận. Không thay đổi API, ingestion worker, schema hoặc hạ tầng production.

## Chuẩn bị

1. Kiểm `kubectl config current-context` là `kind-insighthub-local`; kiểm `kubectl -n insighthub-dev get hpa` không có HPA của API.
2. Áp dụng `chatops-bot/deploy/rbac-local.yaml`. Xác minh read ServiceAccount không được `get secrets` hay `update deployments/scale`, scale ServiceAccount chỉ được `update deployments.apps/insighthub-api --subresource=scale`.
3. Chạy `python tools/mcp/day5/configure.py` để tạo token sáu giờ tại `tmp/day5/`. Tránh in token/kubeconfig ra stdout.
4. Port-forward API, Prometheus, Redis lần lượt đến `127.0.0.1:18000`, `:19090`, `:16380`. Đặt Slack bot token và signing secret trong `tmp/day5/slack.env` quyền `0600`; không commit.
5. Chạy HTTP bot trên `127.0.0.1:18080` và worker riêng. `/healthz` phải trả `ready=true`. Chạy `cloudflared tunnel --no-autoupdate --url http://127.0.0.1:18080`; kiểm HTTPS `/healthz` trước khi nhập Request URL.
6. Trong Slack Event Subscriptions, dùng `https://<quick-tunnel>.trycloudflare.com/slack/events`, subscribe `app_mention`. Tắt Socket Mode nếu dùng HTTP Events API. Kênh test đã mời bot. URL Quick Tunnel là tạm thời, hết hiệu lực khi tunnel dừng.

## Kịch bản E2E

| Thứ tự | Tin nhắn trong `#chatops-test` | Bằng chứng cần thấy |
|---|---|---|
| 1 | `@insighthub-do-2603 api healthy?` | Reply trong thread có readiness, pod, Prometheus 5xx và timestamp; audit có Kubernetes MCP và Prometheus MCP |
| 2 | `@insighthub-do-2603 hôm nay ingest bao nhiêu doc?` | Nói rõ số tài liệu tạo hôm nay theo ICT và hiện ready; không gọi là số hoàn tất lần đầu |
| 3 | `@insighthub-do-2603 pod nào đang lỗi?` | Pod lỗi hoặc thông báo không thấy lỗi; không suy từ phase Running đơn lẻ |
| 4 | `@insighthub-do-2603 delete namespace insighthub-dev` | Denied; không có mutation |
| 5 | `@insighthub-do-2603 scale api to 2` | Trả token 60 giây; deployment vẫn ở replica ban đầu trước confirm |
| 6 | `@insighthub-do-2603 confirm <token>` trong cùng thread bởi approver | API lên 2, audit có approval và outcome verified, replay token bị từ chối |
| 7 | Yêu cầu scale về replica ban đầu, xác nhận bằng token mới | Deployment phục hồi và API ready |

Trước và sau scale lưu `kubectl -n insighthub-dev get deploy insighthub-api -o jsonpath='{.spec.replicas} {.status.readyReplicas}'`. Nếu Kubernetes trả timeout/kết quả không rõ, đọc lại deployment trước khi thử tiếp; không reuse token. Trường hợp tunnel mất kết nối, khởi động lại cloudflared, cập nhật URL rồi gửi event mới. Nếu credentials hết hạn, chạy lại `configure.py` và restart worker.

## Kiểm thử, audit và giới hạn

Chạy `python -m pytest chatops-bot/tests tests/milestones/day5`, Ruff, Mypy và `scripts/verify-day-5.sh --evidence-dir docs/evidence/day5 --bot-transport http --bot-url http://127.0.0.1:18080 --json`. Verifier chỉ kiểm một tập con local, không thay thế link Slack/screencast. Export audit bằng cách chọn các JSON Lines có `event_id` của lượt E2E, lọc token và dữ liệu riêng tư, đặt trong `{ "events": [...] }`; `docs/evidence/day5/day5.json` chứa SHA và source fingerprint hiện hành.

Cloudflared Quick Tunnel không có uptime cố định. Bot chỉ gửi facts đã lọc cho model khi `CHATOPS_MODEL_*` được cấu hình và đích model được cho phép; nếu chưa, câu trả lời deterministic vẫn hoạt động. Không đưa nội dung tài liệu, raw Slack request, token hoặc provider key vào audit/evidence.
