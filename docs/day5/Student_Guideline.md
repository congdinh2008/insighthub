# InsightHub Day 05 - Hướng dẫn thực hành ChatOps cho học viên

Tài liệu này hướng dẫn cài đặt, cấu hình, chạy và kiểm thử bot Day 05 từ source hiện tại. Thực hiện trên **cluster lab local** `kind-insighthub-local`, namespace `insighthub-dev`. Kết quả cần đạt là Slack bot trả lời ba câu hỏi vận hành bằng dữ liệu thật, từ chối lệnh ngoài phạm vi và chỉ scale API sau khi đúng người xác nhận. Không cần sửa API, ingestion worker, web hoặc schema.

**Quy ước lệnh:** mọi terminal đều đứng ở **root repo `insighthub/`**. Các lệnh `kubectl` chỉ dùng context lab. Mỗi `port-forward`, bot, worker và cloudflared chạy trong **terminal riêng** và phải được giữ mở trong lúc test. Không chép token, signing secret, kubeconfig hoặc confirmation token vào Git, ảnh/video hay báo cáo.

## 1. Chuẩn bị trước buổi lab

Đã hoàn thành môi trường Day 03/04: Docker Desktop, `kubectl`, cluster kind, InsightHub API/web/ingestion worker/Redis và Prometheus chạy. Nếu chưa có, làm theo [Day 04 runbook](../day4/Runbook.md) đến bước `make day4-local-status`; không tạo cluster hoặc dataset mới chỉ để chạy Day 05. Máy cần Python 3.12, `cloudflared`, `curl` và quyền tạo Slack App trong workspace lab. Day 02 MCP binaries sẽ được cài bằng installer khóa phiên bản ở bước 2.

Kiểm tra baseline:

```bash
pwd
python3 --version
cloudflared --version
kubectl config current-context
kubectl --context kind-insighthub-local -n insighthub-dev get deploy
kubectl --context kind-insighthub-local -n insighthub-dev get hpa
kubectl --context kind-insighthub-local -n monitoring get service kube-prom-stack-kube-prome-prometheus
```

Chọn đúng context nếu `current-context` khác `kind-insighthub-local`:

```bash
kubectl config use-context kind-insighthub-local
```

Kỳ vọng: API, web, ingestion worker có ready replicas; Redis và Prometheus đang chạy; **không có HPA điều khiển `insighthub-api`**. Nếu HPA tồn tại, dừng bài scale và hỏi giảng viên, không để bot và HPA cùng thay đổi replica. Ghi lại replica gốc trước khi làm bài:

```bash
kubectl --context kind-insighthub-local -n insighthub-dev \
  get deploy insighthub-api -o jsonpath='{.spec.replicas} {.status.readyReplicas}{"\n"}'
```

## 2. Cài dependency và tạo identity tối thiểu

Tạo Python venv **trước khi sinh MCP config** vì config lưu đường dẫn đến Python đang chạy. Repo có thể có `.venv` cũ của Day 01; dùng venv riêng dưới `tmp/day5/` để tránh nhầm runtime.

```bash
mkdir -p tmp/day5
python3 -m venv tmp/day5/venv
tmp/day5/venv/bin/python -m pip install --require-hashes -r chatops-bot/requirements.txt
tmp/day5/venv/bin/python -m pip install --require-hashes -r requirements-dev.txt
python3 tools/mcp/day2/install.py
test -x tmp/day2/bin/kubernetes-mcp-server
test -x tmp/day2/bin/prometheus-mcp-server
```

Installer Day 02 tải binary đã pin và kiểm SHA-256. Nếu đã cài đúng, nó dùng lại bản có sẵn. Không tải MCP server bất kỳ hoặc đổi phiên bản trong bài này.

Tạo hai ServiceAccount và RBAC riêng: một identity chỉ đọc pod/events/log, một identity chỉ có quyền scale deployment `insighthub-api`.

```bash
kubectl --context kind-insighthub-local apply -f chatops-bot/deploy/rbac-local.yaml
kubectl --context kind-insighthub-local -n insighthub-dev \
  auth can-i list pods --as=system:serviceaccount:insighthub-dev:insighthub-day5-bot-readonly
kubectl --context kind-insighthub-local -n insighthub-dev \
  auth can-i get secrets --as=system:serviceaccount:insighthub-dev:insighthub-day5-bot-readonly
kubectl --context kind-insighthub-local -n insighthub-dev \
  auth can-i update deployments.apps/insighthub-api --subresource=scale \
  --as=system:serviceaccount:insighthub-dev:insighthub-day5-scale
kubectl --context kind-insighthub-local -n insighthub-dev \
  auth can-i update deployments.apps/insighthub-web --subresource=scale \
  --as=system:serviceaccount:insighthub-dev:insighthub-day5-scale
```

Kỳ vọng theo thứ tự: `yes`, `no`, `yes`, `no`. `kubectl auth can-i` trả exit code 1 cho kết quả `no`; đây là kết quả deny mong muốn ở lệnh thứ hai và thứ tư. Sinh kubeconfig có token sống 6 giờ và file MCP config trong thư mục Git ignore:

```bash
tmp/day5/venv/bin/python tools/mcp/day5/configure.py
ls -l tmp/day5/readonly.kubeconfig tmp/day5/scale.kubeconfig tmp/day5/mcp.json
```

Kỳ vọng các file có quyền `0600`. Không `cat` hoặc paste nội dung chúng ra chat/log. Khi token hết hạn, chạy lại `configure.py` và restart worker. Read identity không được dùng cho executor scale; scale identity không được dùng cho truy vấn thông thường.

## 3. Mở các kết nối local đến lab

Mở ba terminal mới, mỗi terminal chạy một lệnh và giữ nguyên terminal đó:

```bash
kubectl --context kind-insighthub-local -n insighthub-dev \
  port-forward service/insighthub-api 18000:8000 --address 127.0.0.1
```

```bash
kubectl --context kind-insighthub-local -n monitoring \
  port-forward service/kube-prom-stack-kube-prome-prometheus 19090:9090 --address 127.0.0.1
```

```bash
kubectl --context kind-insighthub-local -n insighthub-dev \
  port-forward service/redis 16380:6379 --address 127.0.0.1
```

Từ terminal thứ tư, kiểm kết nối:

```bash
curl -fsS http://127.0.0.1:18000/readyz
curl -fsS 'http://127.0.0.1:19090/api/v1/query?query=up'
```

API phải trả `status=ready`; Prometheus phải trả `status=success`. Redis sẽ được kiểm qua `/healthz` của bot và test suite. Chỉ bind loopback, không public ba dịch vụ này qua cloudflared. Cổng Prometheus `19090` là cố định trong Day 05 MCP launcher.

## 4. Tạo và cấu hình Slack App

Dùng App riêng của nhóm/học viên trong workspace lab, hoặc App mà giảng viên đã cấp. [Manifest mẫu](../../chatops-bot/config/slack-app-manifest.example.yml) thể hiện cấu hình tối thiểu; sửa tên App cho nhóm, không copy `YOUR_TUNNEL` như URL thật.

1. Trong trang cấu hình Slack App, lấy **App ID** từ URL trang App và **Signing Secret** từ Basic Information. Trong OAuth & Permissions, thêm bot scopes `app_mentions:read` và `chat:write`, rồi Install/Reinstall App vào đúng workspace. Lấy **Bot User OAuth Token** tại đây.
2. Tạo kênh test riêng, ví dụ `#chatops-test`, mời bot vào kênh. Kênh private cũng được nếu bot là thành viên. Ghi **Channel ID** từ URL Slack của kênh.
3. Lấy **Workspace ID** từ URL `app.slack.com/client/T...`; lấy **approver User ID** từ Slack profile của người được giảng viên chỉ định. Không dùng tên hiển thị để kiểm quyền.
4. Tắt Socket Mode khi dùng HTTP Events API. Event Subscriptions và Request URL được bật sau khi cloudflared chạy ở bước 6. Chỉ subscribe bot event `app_mention`; không cấp quyền đọc toàn bộ lịch sử Slack.

Tạo file credential tạm, không đưa giá trị thật vào lệnh shell hoặc tài liệu. Từ root repo:

```bash
umask 077
install -m 600 /dev/null tmp/day5/slack.env
```

Mở `tmp/day5/slack.env` bằng editor và điền các biến sau. Đây là **mẫu cấu trúc**, không chạy trước khi thay giá trị trong dấu `<...>`:

```bash
export SLACK_BOT_TOKEN='<xoxb-token-cua-app>'
export SLACK_SIGNING_SECRET='<signing-secret>'
export SLACK_APP_ID='<A...>'
export SLACK_WORKSPACE_ID='<T...>'
export SLACK_BOT_USER_ID='<U...-bot>'
export CHATOPS_CHANNEL_ID='<C...-hoac-G...>'
export CHATOPS_APPROVER_USER_ID='<U...-approver>'
export CHATOPS_REDIS_URL='redis://127.0.0.1:16380/0'
export CHATOPS_API_URL='http://127.0.0.1:18000'
export CHATOPS_MCP_CONFIG="$PWD/tmp/day5/mcp.json"
export CHATOPS_SCALE_KUBECONFIG="$PWD/tmp/day5/scale.kubeconfig"
export CHATOPS_AUDIT_PATH="$PWD/tmp/day5/chatops-audit.log"
```

Để lấy Bot User ID mà không in token, source file trong terminal riêng rồi gọi Slack `auth.test` bằng SDK đã cài:

```bash
source tmp/day5/slack.env
tmp/day5/venv/bin/python - <<'PY'
import os
from slack_sdk import WebClient
reply = WebClient(token=os.environ['SLACK_BOT_TOKEN']).auth_test()
print('bot_user_id:', reply['user_id'])
print('workspace_id:', reply['team_id'])
PY
```

Điền lại `SLACK_BOT_USER_ID` bằng kết quả và kiểm `workspace_id` trùng giá trị đã chọn. File luôn phải có quyền `0600`; `tmp/` đã được Git ignore. Với App riêng, **phải override mọi ID mẫu của lớp** bằng ID của App/workspace/kênh/người duyệt của nhóm.

## 5. Chạy bot và worker

Mở hai terminal khác, luôn từ root repo. Trong terminal worker:

```bash
source tmp/day5/slack.env
PYTHONPATH=chatops-bot tmp/day5/venv/bin/python -m app.worker
```

Trong terminal HTTP bot:

```bash
source tmp/day5/slack.env
tmp/day5/venv/bin/uvicorn app.main:app --app-dir chatops-bot \
  --host 127.0.0.1 --port 18080
```

Không `cd chatops-bot` rồi chạy worker với đường dẫn tương đối: `CHATOPS_MCP_CONFIG` và audit có thể trỏ sai. Khi mọi thứ sẵn sàng:

```bash
curl -fsS http://127.0.0.1:18080/healthz
```

Kỳ vọng có `"ready":true`, `"transport":"http"`, `"worker_ready":true`. Nếu `worker_ready=false`, kiểm terminal worker và Redis port-forward. Nếu API/Prometheus chưa chạy, `/healthz` vẫn có thể ready nhưng các câu trả lời sẽ là `unknown/partial`; phải kiểm từng upstream ở bước 3.

Model tóm tắt là tùy chọn. Bot vẫn hoạt động khi không đặt `CHATOPS_MODEL_*`. Nếu giảng viên cho phép gửi **facts vận hành đã lọc** tới provider OpenAI-compatible như Zenlayer/DeepSeek, thêm `CHATOPS_MODEL_URL` (base URL kết thúc ở `/v1`), `CHATOPS_MODEL_NAME`, `CHATOPS_MODEL_KEY` vào file `0600`, rồi restart **worker**. Không gửi nội dung tài liệu, raw Slack event hoặc token tới model. Model chỉ viết nhận định tham khảo; code vẫn tự định tuyến, đếm và quyết định quyền.

## 6. Nối Slack qua cloudflared

Mở terminal cloudflared:

```bash
cloudflared tunnel --no-autoupdate --url http://127.0.0.1:18080
```

Ghi URL `https://...trycloudflare.com` mà cloudflared in ra. Kiểm HTTPS `/healthz` với URL đó, rồi trong Slack App > Event Subscriptions bật Events và đặt Request URL là `https://...trycloudflare.com/slack/events`. Slack phải hiện **Verified**. Subscribe `app_mention`, lưu thay đổi. Nếu sửa scope sau đó, Reinstall App vào workspace. Không đặt Request URL trỏ tới API, Redis, Prometheus hoặc Kubernetes.

Quick Tunnel là URL tạm: cloudflared dừng hoặc đổi URL thì Slack sẽ không gửi event được. Khởi động lại cloudflared, cập nhật Request URL và kiểm Verified lại trước khi gửi mention mới. Signing Secret được bot dùng để xác minh HMAC trên raw body; URL challenge không bỏ qua kiểm chữ ký.

## 7. Test hành vi trên Slack thật

Gõ **mention thật** bằng Slack mention picker trong kênh đã cấu hình; gõ chuỗi `@ten-bot` như text thuần có thể không tạo event. Mỗi câu trả lời phải nằm trong thread của tin nhắn gốc. Ghi timestamp và link tin nhắn cho evidence.

| Bước | Gửi trong kênh test | Kỳ vọng cần kiểm |
|---|---|---|
| 1 | `@bot api healthy?` | API readiness, trạng thái pod, 5xx/5m, nguồn và thời điểm. Thiếu dữ liệu phải báo `unknown/partial`, không tự kết luận healthy. |
| 2 | `@bot hôm nay ingest bao nhiêu doc?` | Số document có `created_at` thuộc ngày hiện tại theo ICT và hiện `status=ready`. Đây **không phải** số document hoàn tất lần đầu hôm nay. |
| 3 | `@bot pod nào đang lỗi?` | Tên pod/container lỗi, hoặc không thấy lỗi trong số pod quan sát được; có nguồn Kubernetes MCP. |
| 4 | `@bot delete namespace insighthub-dev` | Từ chối; không có thay đổi cluster. |
| 5 | `@bot scale api to 2` nếu baseline là 1 | Bot hỏi confirm và cho token 60 giây; replica vẫn là baseline **trước** confirm. Nếu baseline khác 1, chọn số khác baseline trong khoảng 1-5. |
| 6 | Đúng approver gửi `@bot confirm <token>` **trong cùng thread** | Deployment đạt replica mới, audit có approval và kết quả verified. |
| 7 | Gửi lại cùng token trong cùng thread | Bị từ chối, replica không đổi. |
| 8 | Scale về baseline bằng yêu cầu và token mới | Replica và readiness trở lại ban đầu. |

Kiểm replica trước/sau bằng lệnh ở bước 1, rồi đợi readiness:

```bash
kubectl --context kind-insighthub-local -n insighthub-dev \
  rollout status deployment/insighthub-api --timeout=90s
kubectl --context kind-insighthub-local -n insighthub-dev \
  get deploy insighthub-api -o jsonpath='{.spec.replicas} {.status.readyReplicas}{"\n"}'
```

Nếu confirm hết hạn hoặc sai người/kênh/thread, tạo yêu cầu mới; không dùng lại token. Nếu lệnh scale trả kết quả chưa rõ, **đọc lại deployment trước** khi tạo yêu cầu khác. Audit là JSON Lines ở `tmp/day5/chatops-audit.log`; kiểm `event_id`, `user`, `action`, `decision`, `tool`, `outcome`. Không chụp hay nộp raw log nếu có dữ liệu nhạy cảm.

## 8. Chạy test tự động và regression

Redis port-forward phải còn chạy; milestone suite dùng Redis database `14` tách khỏi queue bot database `0`. Chạy từ root repo:

```bash
tmp/day5/venv/bin/python -m pytest -q chatops-bot/tests
CHATOPS_REDIS_URL=redis://127.0.0.1:16380/0 \
  tmp/day5/venv/bin/python -m pytest -q tests/milestones/day5
tmp/day5/venv/bin/ruff check chatops-bot/app chatops-bot/tests tests/milestones/day5 tools/mcp/day5
tmp/day5/venv/bin/mypy --follow-untyped-imports --ignore-missing-imports chatops-bot/app
```

Kỳ vọng từ bản source hiện tại: **25 bot tests** và **9 milestone tests** pass, Ruff/Mypy pass. Milestone kiểm signature sai và timestamp cũ, ACK trước xử lý, dedup, worker recovery, policy deny, approval binding/replay. Tests cục bộ không thay thế lượt gửi Slack thật.

Verifier cần `docs/evidence/day5/day5.json` và audit đã lọc, gắn với source fingerprint hiện hành. Sau khi học viên đã tạo evidence của **lượt chạy riêng**, chạy:

```bash
CHATOPS_REDIS_URL=redis://127.0.0.1:16380/0 \
  tmp/day5/venv/bin/python scripts/verify.py day5 \
  --evidence-dir docs/evidence/day5 --bot-transport http \
  --bot-url http://127.0.0.1:18080 --json
```

Evidence mẫu trong repo là của lượt trainer ngày 24/09/2026, **không được dùng để nhận là lượt thực hành của học viên**. Nếu source/evidence thay đổi, cập nhật `source_sha256`, SHA-256 artifact và `observed_at` từ lượt thật; không chỉnh `scripts/verify.py` hoặc tạo fixture để ép PASS. Verifier báo `partial-runtime-contract`, cần đối chiếu thêm link Slack và audit.

Regression upload -> ready -> chat/citation là test **có ghi một document mới vào lab và giữ lại**. Chỉ chạy khi lab cho phép thêm dữ liệu, sau khi mở web port-forward `13000:3000` ở terminal riêng:

```bash
kubectl --context kind-insighthub-local -n insighthub-dev \
  port-forward service/insighthub-web 13000:3000 --address 127.0.0.1
```

```bash
tmp/day5/venv/bin/python scripts/verify.py smoke \
  --api-url http://127.0.0.1:18000 --web-url http://127.0.0.1:13000 \
  --timeout 20 --poll-timeout 60 --json
```

Smoke pass chứng minh pipeline hoạt động trong lab, không chứng minh chất lượng câu trả lời RAG. Sau smoke, số ingestion hôm nay có thể tăng so với snapshot Slack đã chụp trước đó.

## 9. Bàn giao và dọn môi trường

Nộp link Slack cho ba câu đọc, lệnh từ chối, thread approval/scale/replay/restore, trạng thái replica gốc/cuối, audit JSON đã lọc và kết quả tests/verifier. Nếu môn học yêu cầu, quay screencast 3 phút trên kênh test. Mẫu [self-check](Self_Check.md) và [evidence trainer](../evidence/day5/Runtime_Validation.md) chỉ để đối chiếu cách trình bày.

Sau khi lấy đủ evidence, kiểm API đã về baseline, rồi `Ctrl+C` lần lượt ở các terminal cloudflared, bot, worker và port-forward. Quick Tunnel dừng thì Request URL Slack không còn hoạt động; khi học tiếp phải chạy tunnel mới và cập nhật Slack. Không xóa cluster, database, volumes, tài nguyên Day 04 hoặc file của nhóm khác. File `tmp/day5/` chứa token ngắn hạn; giữ ngoài Git và xóa theo chính sách lab sau khi không còn cần chạy lại.

## 10. Chẩn đoán nhanh

| Triệu chứng | Kiểm tra và xử lý |
|---|---|
| Slack Request URL không Verified | Bot/cloudflared phải đang chạy; kiểm đúng `/slack/events`, HTTPS URL mới nhất, Signing Secret và Socket Mode đã tắt. |
| Mention không có reply | Kiểm mention thật, bot là thành viên kênh, `CHATOPS_CHANNEL_ID`, App/Workspace ID, terminal worker và `/healthz`. Kiểm audit theo `event_id`. |
| `/healthz` có `worker_ready=false` | Worker chưa chạy hoặc Redis port-forward lỗi; giữ cả hai terminal mở. |
| Health trả `unknown/partial` | Kiểm API `/readyz`, Prometheus port `19090`, MCP binaries và `tmp/day5/mcp.json`; chạy worker từ root repo, tạo lại config nếu venv/token thay đổi. Không coi dữ liệu thiếu là 0. |
| Count khác kỳ vọng | So sánh ngày ICT, `created_at`, `status=ready` và thời điểm snapshot; tài liệu pending/failed/tạo hôm trước không tính. Smoke có thể đã thêm document mới. |
| Confirm bị từ chối | Kiểm đúng User ID approver, cùng workspace/channel/thread, token còn dưới 60 giây và chưa dùng. Tạo yêu cầu mới thay vì replay. |
| Scale không đạt replica mong muốn | Đọc lại deployment và HPA; kiểm scale ServiceAccount/RBAC, UID/resourceVersion có thể đã đổi; chỉ thử lại sau khi xác minh trạng thái thật. |
| Test milestone không kết nối Redis | Kiểm port-forward `16380`, Redis lab và DB14. Không trỏ test vào Redis production. |
| Model không thêm nhận định | Kiểm ba biến `CHATOPS_MODEL_*`, quyền gửi dữ kiện đã lọc, endpoint/model/key, rồi restart worker; ba intent cốt lõi vẫn trả lời khi model unavailable. |
