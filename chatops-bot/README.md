# InsightHub Day 05 ChatOps

Bot HTTP nhận `app_mention` từ Slack, xác minh chữ ký trước khi ACK, lưu event vào Redis rồi xử lý ở worker riêng. Chỉ có ba câu hỏi đọc: health, tài liệu tạo hôm nay và hiện ready, pod lỗi. Hành động ghi duy nhất là scale `insighthub-api` từ 1 đến 5 replicas trong `insighthub-dev`, sau xác nhận một lần của approver. Lệnh destructive bị từ chối.

## Chạy trong lab local

1. Dùng cluster `kind-insighthub-local`, áp dụng `deploy/rbac-local.yaml`, kiểm tra không có HPA cho API và tạo kubeconfig scoped bằng `python tools/mcp/day5/configure.py` từ thư mục repo. File sinh ra nằm trong `tmp/day5/`, không commit.
2. Port-forward API `18000`, Prometheus `19090`, Redis `16380` trên `127.0.0.1`. Cài dependencies từ `requirements.txt` bằng `--require-hashes`.
3. Cấp `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_APP_ID`, `SLACK_WORKSPACE_ID`, `SLACK_BOT_USER_ID`, `CHATOPS_CHANNEL_ID`, `CHATOPS_APPROVER_USER_ID`, `CHATOPS_REDIS_URL`, `CHATOPS_MCP_CONFIG`, `CHATOPS_SCALE_KUBECONFIG` và `CHATOPS_AUDIT_PATH` qua env hoặc file 0600 dưới `tmp/day5/`. Bot không có quyền đọc Kubernetes Secrets.
4. Chạy `uvicorn app.main:app --app-dir chatops-bot --host 127.0.0.1 --port 18080` và `PYTHONPATH=chatops-bot python -m app.worker` ở hai process riêng. Kiểm `/healthz` có `ready=true`.
5. Chạy `cloudflared tunnel --url http://127.0.0.1:18080` và dùng URL HTTPS được cấp cộng `/slack/events` trong Slack Event Subscriptions. Không mở tunnel cho API, Redis, Prometheus hoặc Kubernetes.

Không commit token, signing secret, kubeconfig hoặc tunnel URL tạm. Quick Tunnel chỉ dùng trong buổi test; nếu tunnel đổi URL, phải cập nhật Slack Request URL rồi xác minh lại challenge. Runtime model là tùy chọn: chỉ bật `CHATOPS_MODEL_URL`, `CHATOPS_MODEL_NAME`, `CHATOPS_MODEL_KEY` khi đích nhận dữ kiện vận hành đã được cho phép. Khi tắt model, bot vẫn trả lời từ dữ kiện có kiểm chứng.

## Contract câu trả lời

- `api healthy?`: đối chiếu `/readyz`, pod qua Kubernetes MCP và HTTP 5xx/5m qua Prometheus MCP. Thiếu nguồn thì trả `unknown/partial`.
- `hôm nay ingest bao nhiêu doc?`: đếm distinct ID từ `GET /documents` có `created_at` thuộc ngày lịch `Asia/Ho_Chi_Minh`, trước thời điểm query, và `status=ready` ở snapshot hiện tại. Đây không phải số lần hoàn tất ingestion đầu tiên hôm nay. Không sửa API/schema để suy diễn timestamp không tồn tại.
- `pod nào đang lỗi?`: đọc pod namespace lab qua Kubernetes MCP; báo phase, readiness hoặc container waiting/terminated reason nếu có.
- `scale api to N`: trả confirmation token 60 giây, chưa thay đổi deployment. `@bot confirm TOKEN` phải từ Slack user ID approver, cùng workspace/channel/thread, và token chỉ dùng một lần. Executor dùng kubeconfig khác với identity đọc, kiểm UID/resourceVersion/replicas trước khi scale.

Audit runtime là JSON Lines append-only. `decision=allowed` là policy, không đồng nghĩa mutation đã thành công; kết quả scale có record riêng. Redis dedup/queue có prefix `insighthub:chatops:` và không dùng ingestion queue. Không cam kết exactly-once khi Slack/API hoặc Kubernetes trả kết quả không rõ.

Chạy kiểm thử: `python -m pytest chatops-bot/tests tests/milestones/day5`. CI chạy cả test, Ruff và Mypy; live Slack/Cloudflare và quyền Kubernetes vẫn cần evidence riêng trong [runbook](../docs/day5/Runbook.md).
