# DAY 05 — ChatOps Bot & Incident Response
## Hướng dẫn Mentor: Slack Bot + Claude Tool-Calling + 3-Tier Permissions

> **Đối tượng:** Trainer / Mentor  
> **Thời lượng:** 2.5 giờ (150 phút)  
> **Branch học viên:** `day5-chatops-bot`  
> **Pre-requisite:** Day 4 PASS — InsightHub observed, Prometheus/Grafana running, MCP servers Day 2 đang Connected

---

## Mục lục

1. [Tổng quan & Mục tiêu](#1-tổng-quan--mục-tiêu)
2. [Chuẩn bị trước buổi](#2-chuẩn-bị-trước-buổi)
3. [Cấu trúc buổi học](#3-cấu-trúc-buổi-học)
4. [Segment 1 — Recap & Hook](#4-segment-1--recap--hook)
5. [Segment 2 — ChatOps Evolution + Architecture](#5-segment-2--chatops-evolution--architecture)
6. [Segment 3 — Slack App Setup + Signature Verify](#6-segment-3--slack-app-setup--signature-verify)
7. [Segment 4 — Live Build: Handler + 3 Intents](#7-segment-4--live-build-handler--3-intents)
8. [Segment 5 — 3-Tier Permission + Audit](#8-segment-5--3-tier-permission--audit)
9. [Segment 6 — Test + Deploy local](#9-segment-6--test--deploy-local)
10. [Artifact Checklist](#10-artifact-checklist)
11. [Troubleshooting Guide](#11-troubleshooting-guide)

---

## 1. Tổng quan & Mục tiêu

### Bức tranh lớn

Day 4: "Ta nhìn thấy sự cố trước user." Day 5: **"Ta triage và response ngay trong Slack không cần mở dashboard."**

Luồng không có bot (trước Day 5):
```
Alert fire → on-call mở Grafana (3 min) → kubectl (5 min) → correlate logs (10 min) → post to Slack (5 min) = 23 phút
```

Luồng với ChatOps 2.0 (sau Day 5):
```
Alert → @bot "api healthy?" → bot query K8s + Prometheus → AI tóm tắt → reply có context trong 5 giây
```

**Key message**: "Detection → Triage → Action through chat — full incident response loop không rời Slack."

### Mục tiêu học viên

| # | Mục tiêu | Artifact |
|---|---|---|
| 1 | Slack signature verify + replay defense | `app/main.py` — `verify_slack_signature()` |
| 2 | BackgroundTasks pattern (< 3s Slack timeout) | `app/main.py` — `_process_and_reply()` |
| 3 | Claude multi-turn tool-calling loop | `app/handler.py` |
| 4 | 3-tier permission (READ / WRITE / DESTRUCTIVE) | `app/permissions.py` |
| 5 | Audit log NDJSON mọi tool call | `app/audit.py` + `chatops-audit.log` |
| 6 | 3 intents hoạt động từ Slack | Demo live |
| 7 | Tests offline pass | `tests/` — `pytest -v` |

### Artifacts học viên nộp

```
chatops-bot/
├── app/main.py          ← verify_slack_signature + BackgroundTasks
├── app/handler.py       ← Claude tool-calling loop (NEW)
├── app/permissions.py   ← 3-tier system (NEW)
├── app/tools.py         ← K8s + Prometheus + API tools (NEW)
├── app/audit.py         ← ghi NDJSON ra file (UPDATED)
├── prompts/system.md    ← Claude system prompt (NEW)
└── tests/               ← 4 test files, ≥ 20 test cases
chatops-audit.log        ← seed file với ≥ 1 NDJSON record
LOOM-URL.txt             ← URL screencast 3 phút
ai-prompts/day5.md       ← ≥ 3 prompts documented
```

---

## 2. Chuẩn bị trước buổi

### 2.1. Slack workspace setup (mỗi học viên tự làm pre-class)

```bash
# 1. Tạo Slack workspace test tại https://slack.com/create
# 2. Tạo Slack App tại https://api.slack.com/apps → Create New App → From scratch
# 3. Lấy: Signing Secret + Bot Token (xref.step 2.2)
# 4. Cài ngrok
brew install ngrok  # hoặc download từ ngrok.com
```

### 2.2. Cấu hình Slack App (Mentor guide học viên làm)

**OAuth & Permissions — Bot Token Scopes cần có:**
- `chat:write` — post messages
- `app_mentions:read` — đọc mentions
- `channels:history` — đọc history (optional cho Day 5)

**Event Subscriptions:**
- Enable → Request URL: `https://<ngrok-url>/slack/events`
- Subscribe to bot events: `app_mention`

**Lấy credentials:**
```
SLACK_SIGNING_SECRET  → Basic Information → App Credentials → Signing Secret
SLACK_BOT_TOKEN       → OAuth & Permissions → Bot User OAuth Token (xox b-...)
```

### 2.3. Kiểm tra Day 2 MCP server (Prometheus + K8s)

Bot Day 5 gọi trực tiếp Prometheus HTTP API và kubectl (reuse ServiceAccount Day 2):

```bash
# Prometheus accessible?
curl -s "${PROMETHEUS_URL:-http://prometheus:9090}/api/v1/query?query=up" | jq '.status'
# → "success"

# kubectl với mcp-readonly ServiceAccount?
kubectl auth can-i get pods --as=system:serviceaccount:insighthub:mcp-readonly -n insighthub
# → yes ✅

# InsightHub API accessible?
curl -s http://localhost:8000/health
# → {"status": "ok"}
```

### 2.4. Install dependencies bot

```bash
cd chatops-bot
pip install -r requirements.txt
# Verify
python -c "import fastapi, anthropic, slack_sdk; print('OK')"
```

### 2.5. Mentor environment variables

```bash
# .env trong chatops-bot/ (KHÔNG commit)
SLACK_SIGNING_SECRET=your_signing_secret_from_slack_app
SLACK_BOT_TOKEN=xoxb-your-bot-token
ANTHROPIC_API_KEY=your_key
INSIGHTHUB_API_URL=http://localhost:8000      # hoặc K8s service URL
PROMETHEUS_URL=http://localhost:9090           # port-forward nếu cần
K8S_NAMESPACE=insighthub
AUDIT_LOG_PATH=chatops-audit.log
```

---

## 3. Cấu trúc buổi học

| Thời gian | Segment | Nội dung |
|---|---|---|
| 0:00–0:10 | Recap & Hook | Từ "observe" → "respond" — MTTR gap |
| 0:10–0:30 | ChatOps Evolution | Gen 1 Hubot → Gen 3 AI agent chat |
| 0:30–0:50 | Slack Setup + Sig | Slack App config + verify_slack_signature |
| 0:50–1:30 | Live Build | handler.py + 3 intents + Claude tool-calling |
| 1:30–1:50 | Permissions + Audit | 3-tier + NDJSON audit log |
| 1:50–2:10 | Test + Deploy | pytest + ngrok + Slack demo live |
| 2:10–2:30 | Verify + Q&A | verify-day-5.sh, rubric review |

---

## 4. Segment 1 — Recap & Hook

**Hook question (2 phút):**
> "Day 4 bạn có alert InsightHubQueueDepthAnomaly fire lúc 3h sáng. On-call bạn mở máy tính. Thứ đầu tiên họ làm là gì? Mở Grafana — mất ít nhất 3 phút để orient. Day 5: thứ đầu tiên họ làm là nhắn Slack."

**Demo MTTR gap (3 phút):**

| Không có bot | Với bot |
|---|---|
| Mở Grafana (3 min) | @bot "api healthy?" (5 sec) |
| Chạy kubectl (3 min) | @bot "which pods failing?" (5 sec) |
| Correlate logs (10 min) | Bot tự correlate + trả lời với context |
| Post Slack update (5 min) | Bot đã post trong cùng thread |
| **~21 phút** | **~30 giây** |

**Warning trước lab (1 phút):**
> "Bot nào biết gọi kubectl thì cũng biết kubectl delete. Hôm nay học cả cách làm bot an toàn — không phải chỉ làm bot nhanh."

---

## 5. Segment 2 — ChatOps Evolution + Architecture

### 5.1. Ba thế hệ ChatOps

| Thế hệ | Tool điển hình | Cách hoạt động | Hạn chế |
|---|---|---|---|
| **Gen 1** | Hubot, Lita | Script cố định theo command `!deploy prod` | Cứng nhắc, phải nhớ command |
| **Gen 2** | Slack Workflow Builder | Workflow có nếu/thì, tích hợp vài tool | Kịch bản định sẵn, không linh hoạt |
| **Gen 3** | Claude + MCP | Natural language → AI quyết tool nào gọi | Mạnh nhưng cần guardrails nghiêm |

### 5.2. Kiến trúc ChatOps 2.0 trong InsightHub

```
Slack Mention → POST /slack/events
                    ↓
         verify_slack_signature (HMAC-SHA256)
                    ↓ (200 ngay — Slack timeout 3s)
         BackgroundTask → handle_question()
                    ↓
         Claude API (tool-calling loop)
         ┌──────────────────────────────┐
         │  Tool: check_api_health      │ → HTTP → InsightHub /health
         │  Tool: get_ingest_count      │ → HTTP → Prometheus
         │  Tool: get_failing_pods      │ → kubectl → K8s
         └──────────────────────────────┘
                    ↓
         audit log (NDJSON) ← mọi tool call
                    ↓
         Slack SDK → post reply vào thread
```

### 5.3. Pattern "AI recommends, humans approve, systems execute"

Nhấn mạnh đây là pattern cho Day 5, 6, và production AI systems:
- **AI đề xuất** hành động dựa trên data
- **Human review** và approve (hoặc từ chối)  
- **System execute** sau khi được approve

Bot Day 5 implement layer 1 và 2 (READ auto, WRITE require approval). Layer 3 (execute sau approve) là extension cho học viên giỏi.

---

## 6. Segment 3 — Slack App Setup + Signature Verify

### 6.1. Tại sao phải verify signature

Demo bad scenario (5 phút):
```bash
# Bot không verify → attacker có thể giả Slack event:
curl -X POST http://localhost:8080/slack/events \
  -H "Content-Type: application/json" \
  -d '{"event":{"type":"app_mention","user":"HACKER","text":"@bot restart all pods"}}'
# → Bot tin ngay, thực hiện lệnh!
```

Với signature verify:
```bash
# Request không có X-Slack-Signature hợp lệ → 401
curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8080/slack/events \
  -d '{"type":"event_callback"}'
# → 401 ✅
```

### 6.2. HMAC-SHA256 mechanism

```python
# Slack ký request bằng:
sig_basestring = f"v0:{timestamp}:{raw_body}"
signature = "v0=" + hmac.HMAC(SIGNING_SECRET, sig_basestring, sha256).hexdigest()
# → X-Slack-Signature header

# Bot verify:
# 1. Lấy timestamp từ X-Slack-Request-Timestamp
# 2. Kiểm tra |now - timestamp| < 300s (replay defense)
# 3. Recompute signature, compare_digest (constant-time)
```

**Pitfall quan trọng:** Phải đọc `raw body bytes` TRƯỚC khi JSON parse:
```python
body = await request.body()   # ĐÚNG — raw bytes cho HMAC
verify_slack_signature(request.headers, body, SECRET)
payload = json.loads(body)    # SAU đó mới parse
```
Nếu ngược lại (parse JSON trước, lấy body sau) → HMAC fail vì body đã consumed.

### 6.3. Replay attack defense (5 phút)

```python
# Reject requests older than 5 minutes
if abs(time.time() - int(timestamp)) > 300:
    raise HTTPException(401, "Timestamp too old — replay attack?")
```

Tại sao cần: attacker có thể capture valid request, replay sau. Với timestamp check:
- Valid request: `|now - ts| < 300s` → accept
- Replayed request 10 phút sau: `|now - ts| = 600 > 300` → reject

---

## 7. Segment 4 — Live Build: Handler + 3 Intents

### 7.1. Claude tool-calling loop (demo 15 phút)

Demo trực tiếp tại màn hình — Claude API tool use multi-turn:

```python
# Round 1: User asks, Claude decides which tool to call
messages = [{"role": "user", "content": "InsightHub có healthy không?"}]
response = claude.messages.create(model=..., tools=TOOL_DEFINITIONS, messages=messages)
# Claude returns: [ToolUseBlock(name="check_api_health", input={})]

# Execute tool
result = await check_api_health()  # → {"status": "ok", "http_code": 200}

# Round 2: Claude synthesizes answer
messages += [
    {"role": "assistant", "content": response.content},
    {"role": "user", "content": [{"type": "tool_result", "content": json.dumps(result)}]},
]
response = claude.messages.create(...)
# Claude returns: TextBlock("InsightHub is *healthy* ✅ — API returned HTTP 200.")
```

**Điểm nhấn giảng dạy:**
- Loop tối đa 5 vòng tránh infinite loop
- Claude tự quyết tool nào gọi — không hard-code intent routing
- Tool execution xảy ra bên ngoài Claude (ở Python code) — Claude chỉ quyết định WHAT, không HOW

### 7.2. Ba tools và cách inject (demo testability)

```python
# Tools nhận optional client cho testability
async def check_api_health(client: httpx.AsyncClient | None = None) -> dict:
    c = client or httpx.AsyncClient()
    # ...

# Trong test: inject mock client
mock_client = AsyncMock()
result = await check_api_health(client=mock_client)
```

Nhấn mạnh: **injectable dependency là pattern cho production code**, không chỉ để test. Cùng tool function có thể dùng với client khác nhau (staging, prod, test).

### 7.3. Mapping 3 câu hỏi → 3 tools

| Câu hỏi Slack | Tool được gọi | Data source |
|---|---|---|
| "api healthy?" / "InsightHub OK không?" | `check_api_health` | `GET /health` của InsightHub API |
| "ingest count hôm nay?" / "bao nhiêu doc?" | `get_ingest_count_today` | Prometheus `increase(...[24h])` |
| "pod nào lỗi?" / "which pods failing?" | `get_failing_pods` | `kubectl get pods -o json` |

---

## 8. Segment 5 — 3-Tier Permission + Audit

### 8.1. 3-tier permission design

Demo phân tích từng tier (10 phút):

```python
# Tier 1: READ — auto allowed
"api healthy?" → PermissionTier.READ → gọi tool luôn

# Tier 2: WRITE — ask confirm
"scale api to 5" → PermissionTier.WRITE → issue token
# Bot reply: "⚠️ Confirm: reply `confirm <token>` within 60s"

# Tier 3: DESTRUCTIVE — always deny
"delete pod api-0" → PermissionTier.DESTRUCTIVE → block
# Bot reply: "⛔ Destructive actions blocked. Use runbook."
```

**Thảo luận với lớp (5 phút):**
> "Tại sao WRITE không cho phép luôn? Bởi vì bot đang chạy với ServiceAccount có quyền scale. Ai cũng trong channel đó đều có thể mention bot — không phải ai cũng có quyền scale production."

**Confirmation token pattern:**
```python
# Token: one-time-use, 60s TTL, user-bound
token = secrets.token_urlsafe(16)
_token_store[token] = (user_id, monotonic() + 60)

# Validate và consume
if validate_confirmation_token(token, user_id):
    # execute write action
```

### 8.2. Audit log — "Không có audit = không có trách nhiệm"

**Demonstrate value:**
```bash
cat chatops-audit.log | jq -s '.' | head -20
# → Array of records: ts, user, tool, args, result, approved
```

Dùng audit log để trả lời câu hỏi:
- "Ai đã chạy kubectl lúc 3h sáng?" → `jq '.user' chatops-audit.log | sort | uniq -c`
- "Tool nào được gọi nhiều nhất?" → `jq '.tool' chatops-audit.log | sort | uniq -c | sort -rn`
- "Action nào bị từ chối?" → `jq 'select(.approved==false)' chatops-audit.log`

**Format NDJSON (một dòng một record):**
```json
{"ts":"2026-06-04T10:00:00+00:00","user":"U123","tool":"check_api_health","args":{},"result":"{'status':'ok'}","approved":true}
```

Lý do NDJSON: append-only, không cần lock file, `jq -s` ghép thành array khi cần.

---

## 9. Segment 6 — Test + Deploy local

### 9.1. Chạy tests offline

```bash
cd chatops-bot
pytest tests/ -v
# Expected: 36 passed in <1s — không cần API key, không cần K8s
```

**Điểm giảng dạy quan trọng:**
> "Tests 100% offline vì trainer CI không có Slack/Anthropic/K8s credentials. Bất kỳ test nào require network là test sẽ fail trên CI của học viên khác."

Demo fail → fix cycle (5 phút): sửa 1 test để nó fail, chạy lại, sửa code:
```bash
pytest tests/test_signature.py::TestVerifySlackSignature::test_old_timestamp_rejected -v
```

### 9.2. Chạy bot local + ngrok

```bash
# Terminal 1: start bot
cd chatops-bot
uvicorn app.main:app --port 8080 --reload

# Terminal 2: ngrok
ngrok http 8080
# → Forwarding https://abc123.ngrok-free.app → localhost:8080

# Verify health
curl http://localhost:8080/healthz
# → {"status":"ok","service":"chatops-bot"}

# Test invalid signature → 401
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8080/slack/events \
  -H "Content-Type: application/json" -d '{"type":"event_callback"}'
# → 401 ✅
```

Trỏ Slack App Event Subscription URL: `https://abc123.ngrok-free.app/slack/events`

### 9.3. Demo live trong Slack (10 phút)

Chuẩn bị Slack channel `#insighthub-ops`. Invite bot. Demo 4 câu:

```
@chatops-bot api healthy?
@chatops-bot ingest count hôm nay?
@chatops-bot pod nào đang lỗi?
@chatops-bot scale api to 10 replicas
```

Kết quả kỳ vọng:
- Câu 1-3: bot trả lời với data thật trong < 5s
- Câu 4: bot reply "⚠️ Confirm: reply `confirm <token>` within 60s"

Verify audit log sau demo:
```bash
cat chatops-bot/chatops-audit.log | jq -s 'length'
# → số lượng tool calls đã thực hiện
```

---

## 10. Artifact Checklist

```bash
cd insighthub
bash scripts/verify-day-5.sh
# Expected: 8/8 PASS
```

Chi tiết các check:

| Check | Command | Expected |
|---|---|---|
| Structure | `ls chatops-bot/app/` | main.py, audit.py, permissions.py |
| Signature | `grep -E "hmac\|verify_signature" chatops-bot/app/*.py` | match found |
| No NotImplementedError | `grep "NotImplementedError" chatops-bot/app/main.py` | no match |
| Audit log format | `jq -c '.' chatops-bot/chatops-audit.log \| head -1 \| jq '.ts and .user and .tool'` | true |
| Loom URL | `cat LOOM-URL.txt \| grep loom.com` | URL exists |
| Tests | `cd chatops-bot && pytest tests/ -q` | all passed |

Manual checks thêm (trainer):
```
[ ] Bot trả lời 3 câu hỏi trong Slack (demo hoặc screencast)
[ ] Slack: @bot "scale api" → bot xin confirmation token
[ ] Slack: @bot "delete pod" → bot từ chối ⛔
[ ] Audit log có ≥ 3 records với ts/user/tool đầy đủ
[ ] LOOM-URL.txt có URL loom.com thật (không phải placeholder)
```

---

## 11. Troubleshooting Guide

### Bot nhận mention nhưng không reply

```bash
# Kiểm tra SLACK_BOT_TOKEN được set
echo $SLACK_BOT_TOKEN | head -c 10
# → xoxb-...

# Check bot logs
cd chatops-bot && uvicorn app.main:app --port 8080 2>&1 | grep -E "ERROR|WARNING"

# Thường gặp: bot reply to itself (infinite loop)
# Fix: event filter đã có trong main.py — kiểm tra bot_user_id check
```

### Slack signature mismatch — 401 với request hợp lệ

```bash
# Nguyên nhân phổ biến: đọc body SAU khi json.loads
# → body đã consumed, HMAC tính trên empty string

# Fix đúng: đọc raw bytes TRƯỚC:
body = await request.body()          # PHẢI làm đầu tiên
verify_slack_signature(headers, body, SECRET)
payload = json.loads(body)           # SAU đó mới parse
```

### `kubectl` timeout trong bot

```bash
# Bot chạy local nhưng kubectl context trỏ cluster không accessible
kubectl config current-context
kubectl get pods -n insighthub --request-timeout=5s

# Fix: set đúng context
kubectl config use-context insighthub-lab

# Hoặc sửa KUBECONFIG trong .env:
KUBECONFIG=/path/to/your/kubeconfig
```

### Prometheus query trả về empty result

```bash
# Kiểm tra metric tồn tại
curl -s "http://localhost:9090/api/v1/query?query=insighthub_ingestion_jobs_total" | jq '.data.result'

# Nếu empty → metric chưa có hoặc tên sai
# Bot sẽ trả về: {"count": 0, "source": "prometheus_error"}
# Đây là behavior đúng — không crash

# Verify tên metric trong InsightHub API
curl -s localhost:8000/metrics | grep insighthub_ingestion
```

### Claude tool-calling loop không dừng

```bash
# Symptom: log thấy 5+ rounds liên tục
# Đã có guard: _MAX_TOOL_ROUNDS = 5 trong handler.py
# Nếu vượt quá → trả "Unable to complete query after multiple attempts."

# Debug: log từng round
uvicorn app.main:app --port 8080 --log-level debug
```

### Audit log không tạo được

```bash
# Check quyền ghi
ls -la chatops-bot/
touch chatops-bot/test.log && rm chatops-bot/test.log   # nếu fail → quyền bị chặn

# Check AUDIT_LOG_PATH
cd chatops-bot && python -c "import app.audit; print(app.audit.AUDIT_LOG_PATH)"
# Phải là: chatops-audit.log (relative → tạo trong thư mục hiện tại = chatops-bot/)

# Seed file cho verify script
echo '{"ts":"2026-01-01T00:00:00+00:00","user":"U0","tool":"init","args":{},"result":"seed","approved":true}' \
  > chatops-bot/chatops-audit.log
```

### ngrok URL thay đổi sau restart

```bash
# Free tier ngrok đổi URL mỗi lần restart
# → phải update Slack App Event URL mỗi lần

# Solution: ngrok paid tier với static domain
ngrok http 8080 --domain your-domain.ngrok-free.app

# Hoặc deploy bot lên K8s với Ingress (nice-to-have Day 5)
```

### Bot timeout 3s trong Slack

```bash
# Slack retry nếu không nhận 200 trong 3s
# Fix: BackgroundTasks đã implement — kiểm tra không gọi handle_question() inline

# Sai (block 3s):
async def slack_events(request: Request):
    answer = await handle_question(question, user_id)  # ← chặn!
    return {"ok": True}

# Đúng (return ngay):
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    background_tasks.add_task(_process_and_reply, question, ...)
    return {"ok": True}   # ← ngay lập tức
```
