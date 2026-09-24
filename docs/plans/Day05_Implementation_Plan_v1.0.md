# InsightHub - Kế hoạch hoàn thiện Day 05

**Phiên bản:** 1.0 | **Ngày:** 24/09/2026 | **Trạng thái:** Đã triển khai và nghiệm thu runtime; video/PR chờ điều kiện bàn giao.

**Baseline đã khảo sát:** local `main`, commit `7613ba0`, Day 04 đã merge; working tree sạch trước khi tạo tài liệu này.

**Mục tiêu:** Hoàn thiện ChatOps Day 05 theo MH1-MH11, functional/non-functional acceptance và rubric L3. Tập trung vào DevOps và chatbot; giữ nguyên business code, schema và ingestion pipeline của InsightHub.

## 1. Nguồn yêu cầu và quyết định phạm vi

Thứ tự áp dụng:

1. Chỉ đạo của anh Công trong task ngày 24/09/2026: nghiên cứu và lập plan Day 05, không làm vượt yêu cầu. Với ingestion count, anh chọn **phương án tránh sửa code ứng dụng, tập trung DevOps/Chatbot**.
2. [Specification v3.3](../../Running-Project-Specification-Student.md), mục 0.2-0.4, 4 và 9: nguồn Must-have, acceptance, rubric và submission.
3. [Lab guide Day 05](../lab-guides/Day5-ChatOps-Incident-Response.md), [AGENTS.md](../../AGENTS.md), [verification contract](../../scripts/VERIFICATION_CONTRACT.md) và [verifier](../../scripts/verify.py).
4. [Transcript Day 05](<../../../9. AI for Devops/06_Customize/DO2603/05_Delivery/Day5_Transcript_20260922/Transcript_Day5_ChatOps_Incident_Response_v1.0.md>): tham khảo data semantics, approval và test cases. Các ví dụ synthetic không phải evidence runtime.
5. Source và [evidence Day 04](../evidence/day4/Runtime_Validation.md): cơ sở tái sử dụng, không tự chuyển thành evidence Day 05.

### Trong phạm vi

- FastAPI `/slack/events`, Slack SDK, kết nối HTTP qua cloudflared đã cài trên máy và Slack App thật.
- Xác thực raw-body signature/timestamp; ACK <3 giây; durable queue, dedup, bounded retry và worker xử lý sau.
- Ba intent: health, ingestion hôm nay theo contract đã chọn, pods lỗi.
- Bot thực sự gọi Kubernetes MCP và Prometheus MCP đã dùng Day 02/04, với config và identity riêng.
- Ba tầng quyền, một thao tác ghi duy nhất là scale API trong lab, approval ràng buộc chính xác hành động, audit JSON.
- Tests, evidence live, runbook, prompt log theo spec, self-check, PR và screencast 3 phút.

### Ngoài phạm vi

- Không sửa `api/`, `ingestion-worker/`, `web/`, `infra/db/init.sql`, schema, vector/embedding identity hoặc business feature.
- Không thêm `completed_at`, completion ledger, metric nghiệp vụ hoặc endpoint ứng dụng mới. Không sửa MCP nội bộ chỉ để bổ sung timestamp cho count.
- Không xây autonomous remediation, auto-RCA/postmortem, `/catchup`, service catalog, Slack Block Kit/interactivity hoặc agent loop tự do.
- Không dựng bot production trên EKS, IRSA, public Kubernetes Ingress/TLS, HPA mới, Loki, A2UI, dashboard/monitoring mới cho bot.
- Không làm Promptfoo, LiteLLM, FinOps hay các nội dung Day 06. Không provision lại AWS.
- Không sửa specification hoặc verifier/assertions để đạt PASS. Không tạo quiz mới vì Day 05 không có quiz trong Must-have.

**Xử lý các chỗ chồng lấn trong spec:** Replay defense nằm ở Should-have nhưng timestamp >5 phút đã là NFR bắt buộc. Confirmation token nằm ở Should-have nhưng acceptance bắt buộc bot hỏi confirm với token khi scale. Vì vậy vẫn làm hai phần này ở mức tối thiểu; không thêm toàn bộ Should-have hoặc các mục L4.

## 2. Hiện trạng và khoảng trống

| Hạng mục | Hiện trạng có căn cứ | Phần còn thiếu |
|---|---|---|
| Day 01-04 | Day 04 đã merge vào local `main`; có dashboard, anomaly/RCA và Slack alert evidence | Kiểm lại dependency khi bắt đầu Day 05, không dựng lại bài Day 04 |
| Runtime local | Đã đọc trạng thái `kind-insighthub-local/insighthub-dev`: web, API, worker Ready 1/1; PostgreSQL/Redis Ready 1/1; fault proxy Ready 1/1 | Đây chỉ là snapshot workload, chưa chứng minh toàn hệ thống healthy hoặc bot hoạt động |
| Bot | `chatops-bot/app/main.py`: `/healthz` trả `ready=false`, `/slack/events` trả 501; handler chưa implement | Hoàn thiện transport, queue, xử lý câu hỏi, reply và readiness |
| Dependencies | Bot mới có FastAPI/Uvicorn; Dockerfile non-root và dependency hashes đã có | Bổ sung Slack SDK, MCP client và queue client đúng phiên bản kiểm chứng; pin/hashes |
| Audit | `audit.py` ghi tiền tố `AUDIT`, dùng `approved=True`, chưa đủ event correlation/policy semantics | JSON Lines thực, durable sink và format evidence tương thích verifier |
| MCP | Có binaries pin Day 02; Day 04 trỏ namespace `insighthub-dev` và Prometheus local | Runtime bot phải initialize/list/call thật, không chỉ dùng config MCP của coding host |
| Health/pods | Có Prometheus và Kubernetes metadata phục vụ triage | Chuẩn hóa dữ liệu, scope, freshness, lỗi và cách trả lời |
| Ingestion count | `/documents` có `id`, `created_at`, `status`; chưa có thời điểm hoàn tất. MCP list documents chỉ trả tối đa 20 bản ghi và bỏ `created_at` | Bot đọc endpoint có sẵn, tự tính theo contract mục 3; không dùng danh sách MCP bị cắt để đếm tổng |
| Permissions | Chưa có approval store, mutation identity hoặc executor | Tách read identity và scale identity, gate thực ở backend |
| Tests/CI | Chưa có `chatops-bot/tests/` và `tests/milestones/day5/`; CI chưa chạy bot suite | Thêm tests Day 05 và bước CI phù hợp |
| Slack | Day 04 đã chứng minh incoming webhook gửi alert tới `#alerts` | Chưa chứng minh bot token, signing secret, scopes, event URL và mention/reply Day 05 |

Không lấy incoming webhook của Alertmanager làm bằng chứng bot đã có quyền nhận event hoặc gọi `chat.postMessage`.

## 3. Contract ba intent

Mọi câu trả lời có môi trường/namespace, thời điểm quan sát, dữ kiện và phần chưa xác minh. Dữ liệu thiếu hoặc tool lỗi phải giữ trạng thái unknown/partial; không biến thành 0 hoặc healthy.

| Intent | Nguồn và xử lý | Câu trả lời cần đạt |
|---|---|---|
| `InsightHub có healthy không?` / `api healthy?` | MCP Prometheus: targets, RED, queue, dependency signals hiện có; MCP K8s: pod/container readiness. Có thể đọc `/readyz` có sẵn để đối chiếu API | Healthy/degraded/unknown theo tín hiệu và ngưỡng đã cấu hình cho lab; nêu evidence + timestamp. `up=1` hoặc Pod Running không đủ để kết luận healthy |
| `Hôm nay ingest bao nhiêu doc?` / `ingest count today?` | Bot read adapter gọi cố định `GET /documents`, lọc ID distinct theo ngày tạo và `status=ready`; Prometheus MCP bổ sung trạng thái queue/inventory khi cần | “Có N tài liệu được tạo hôm nay và hiện đã ready”, kèm khoảng thời gian, timezone và hạn chế của phép đếm |
| `Pod nào đang lỗi?` / `which pods failing?` | MCP K8s đọc pods, container waiting/terminated, conditions, readiness, restart count; events/logs có giới hạn nếu cần | Pod/container/reason, namespace, observed_at và bước kiểm tra tiếp theo; phát hiện cả CrashLoopBackOff trong pod phase Running |

### Quyết định ingestion count theo chỉ đạo của anh Công

**Định nghĩa triển khai:** số document hiện còn trong API, có `created_at` thuộc ngày lịch hiện tại theo `Asia/Ho_Chi_Minh` và `status=ready` tại snapshot query.

- Chốt `query_end` trước khi gọi API. Cửa sổ là `[00:00 hôm nay, query_end)`, chuyển sang UTC để so sánh timestamp; không dùng rolling 24h.
- Đếm distinct `id`; pending/failed và tài liệu tạo trước hôm nay không tính. Tài liệu đã xóa không nằm trong inventory hiện tại và không được hồi dựng.
- Giá trị do code của chatbot tính, không để LLM tự đếm hoặc tự viết SQL/PromQL.
- Chỉ giữ `id`, `created_at`, `status` trong bước tính; không đưa filename, nội dung tài liệu hoặc embedding metadata vào model/audit.
- Adapter có URL/method cố định, timeout và giới hạn response. Response bị cắt, quá lớn hoặc sai schema phải trả lỗi/partial, không công bố số tổng thiếu.
- Không lấy `increase(insighthub_documents_total[...])`: đây là Gauge inventory. Không coi `insighthub_worker_jobs_total{outcome="ready"}` là số document distinct vì redelivery có thể tăng counter.
- Endpoint hiện trả danh sách, chưa có aggregate/pagination server-side. Đây là giới hạn được chấp nhận cho lab nhỏ; không mở rộng API để tối ưu trong Day 05.

**Điểm khác với case completion trong học liệu:** kết quả này không chứng minh tài liệu hoàn tất ingestion lần đầu trong ngày. Tài liệu tạo hôm qua nhưng hoàn tất hôm nay sẽ không được tính. Câu trả lời, tests, README và screencast phải dùng cùng định nghĩa; không âm thầm gọi đây là exact first-completion count. Đây là quyết định phạm vi của trainer trong task này.

## 4. Kiến trúc triển khai tối thiểu

```text
Slack @mention
  -> cloudflared HTTPS
  -> FastAPI: raw-body auth + event filtering + durable enqueue
  -> HTTP ACK <3s

Redis queue riêng cho ChatOps
  -> ChatOps worker: route intent -> collect evidence -> LLM summary
       -> Kubernetes MCP (read-only identity)
       -> Prometheus MCP (query tools)
       -> fixed GET /documents hoặc /readyz đã có
  -> Slack SDK: reply trong thread
  -> JSON audit

Scale request
  -> policy -> pending approval + token
  -> signed confirmation từ approver được phép
  -> atomic consume -> executor với scale identity riêng
  -> kiểm kết quả + audit + restore trong demo
```

### 4.1. Môi trường

- Bot chạy local bằng FastAPI/Uvicorn và queue worker riêng; dùng cluster Day 03/04 hiện có. Cloudflared chỉ public cổng bot, không public API, Prometheus hoặc Redis.
- Tái sử dụng Redis lab có persistence, nhưng dùng queue/job IDs/dedup/approval keys prefix riêng `insighthub:chatops:*`; không đọc/xóa key ingestion. Port-forward nếu cần chỉ bind loopback.
- Chưa thêm broker, database hoặc framework orchestration mới. Dùng queue client theo ARQ/Redis đã quen trong repo nếu kiểm chứng tương thích.
- Giữ Dockerfile chạy được, pin dependencies, copy thêm prompt/config cần thiết, bảo đảm audit path writable. Local execution là đường nghiệm thu chính; image không đồng nghĩa phải deploy bot production.
- Giữ provider/model đang dùng được cấu hình qua runtime env cho chatbot. Không đổi provider hoặc embedding của InsightHub; không route gateway Day 06.
- Slack bot token và signing secret do operator cấu hình trong Secret của cluster lab; local bot nhận qua cơ chế inject env/file bảo vệ ngoài Git. Bot read identity không có quyền đọc Secrets. Không in secret vào terminal/evidence.

### 4.2. HTTP intake, ACK và reliability

1. Đọc raw bytes; kiểm signature bằng signing secret và timestamp trước parse JSON, trước trả `url_verification.challenge`.
2. Reject chữ ký thiếu/sai, timestamp malformed hoặc lệch quá 300 giây cả quá khứ/tương lai. Thiếu signing secret thì fail closed. Slack hướng dẫn kiểm raw body, HMAC và so sánh chữ ký an toàn tại [request verification](https://docs.slack.dev/authentication/verifying-requests-from-slack/).
3. Kiểm workspace/app/channel đã cấu hình; chỉ nhận `app_mention` cần thiết. Bỏ bot messages, self messages và subtype không hỗ trợ để tránh reply loop.
4. Lưu event chuẩn hóa và dedup key `(workspace_id, event_id)` vào durable state trước ACK. Enqueue/dedup phải nguyên tử hoặc có cơ chế recovery đã test; không đặt cờ dedup rồi đánh mất job.
5. ACK event được nhận thành công hoặc duplicate đã lưu trong <3 giây. Queue không sẵn sàng thì trả lỗi retriable trước deadline; không ACK thành công khi chưa lưu được việc.
6. Worker thực hiện MCP/LLM và gửi reply sau. Deadline đề xuất cho một câu trả lời là 30 giây; dùng handler cố định, giới hạn tool calls theo intent và tối đa hai lượt model: nhận diện intent nếu cần, rồi tổng hợp. Không xây multi-step agent tổng quát.
7. Retry lỗi tạm thời có giới hạn; Slack 429 tôn trọng `Retry-After`. Trạng thái xử lý và kết quả trả lời được lưu để worker restart không tự chạy lại toàn bộ tác vụ đã xong.
8. Kiểm duplicate đồng thời, worker chết sau enqueue và lỗi khi gửi reply. Không tuyên bố exactly-once giữa Redis, Slack và Kubernetes; outcome chưa rõ phải reconcile, đặc biệt không retry mutation mù.

Slack quy định ACK trong ba giây và có cơ chế redelivery khi thất bại, nên event identity và durable acceptance là phần bắt buộc của thiết kế. [Slack Events API](https://docs.slack.dev/apis/events-api/).

### 4.3. Runtime MCP và model

- Reuse binaries/version pin Day 02; tạo config Day 05 riêng thay vì đổi config host Day 04. Khởi tạo MCP client, negotiate protocol, `tools/list`, `tools/call`, lưu trace đã lọc.
- Kubernetes MCP giới hạn một context/namespace và tool đọc cần thiết: pods, events, logs có giới hạn. Prometheus MCP chỉ query/range/targets tới endpoint lab đã cấu hình.
- Chặn tool lạ, params ngoài schema, namespace/URL do model tự chọn và các tool mutation. Tách tên tool theo backend để không nhầm registry.
- LLM chỉ route/tổng hợp dữ kiện trong contract hẹp; không quyết định permission, không tự tính count và không coi log/tool output là chỉ dẫn.
- Tool timeout, `isError`, empty result và stale data được giữ trong result contract. Facts/count còn hợp lệ có thể trả bằng template khi model lỗi, kèm trạng thái lỗi; không giả vờ LLM đã thành công.
- Bot phải gọi hai backend thật. CLI chỉ hỗ trợ setup/debug, không thay bằng chứng MCP runtime. [MCP client concepts](https://modelcontextprotocol.io/docs/2026-07-28/learn/client-concepts).

### 4.4. Ba tầng quyền và scale approval

| Tier | Quyết định | Backend enforcement |
|---|---|---|
| Read | Tự thực thi sau khi xác thực và đúng allowlist | ServiceAccount riêng chỉ đọc namespace lab; không Secrets, exec hoặc write |
| Write | `approval_required`; chỉ hỗ trợ scale `insighthub-api` trong lab | Approver allowlist, action token một lần, executor identity riêng chỉ được thao tác scale đúng resource |
| Destructive | Nhận diện và deny trong lab Day 05 | Không có delete/destructive executor; token cho scale không mở được quyền destructive |

- Hỗ trợ câu `scale api to 5`, validate replica integer trong khoảng lab đã chốt, đề xuất 1-5. Không cần slash command hoặc nút interactive.
- Confirmation dùng reply `@bot confirm <token>`; TTL đề xuất 60 giây. Token được tạo/kiểm ở backend, không chuyển qua LLM và không lưu raw token vào audit.
- Record gắn `workspace_id`, requester, allowed approver, action, cluster, namespace, target UID, exact replicas, precondition, expiry và operation ID.
- Sai người, workspace, target, args, UID/precondition; token hết hạn hoặc đã dùng đều bị từ chối. Atomic consume bảo đảm hai confirmation đồng thời không cùng khởi động hai mutation.
- Executor chạy bằng credential khác read MCP, chỉ scale Deployment API được allowlist; không chạy shell từ text/model. Phạm vi RBAC dùng namespace, subresource và resource name cụ thể. [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).
- Trước live test kiểm API HPA thực tế. Local values hiện tắt HPA; nếu runtime có HPA hoặc actor khác quản lý replica thì dừng để xử lý đúng ownership, không tự xóa HPA.
- Demo lưu replicas ban đầu, xác nhận chưa đổi trước approval, scale sau approval rồi đọc kết quả. Nếu timeout sau gửi mutation, đọc lại trạng thái trước quyết định retry; không dùng lại token cũ.
- Restore replicas ban đầu bằng một hành động được xác nhận riêng hoặc operator theo runbook, rồi kiểm API healthy. Không dùng scale demo để tuyên bố đã sửa một incident bất kỳ.

Destructive deny phù hợp phần lab của transcript Day 05; không triển khai xóa namespace/data để chứng minh ba tầng quyền. Approval của scale vẫn là Must-have dù rubric L4 cũng nhắc approval gate.

### 4.5. Audit

- Mỗi tool call, policy decision và execution outcome có record JSON; file runtime `chatops-audit.log` ghi một object mỗi dòng, không thêm tiền tố text.
- Field tối thiểu: `timestamp`, `event_id`, `workspace_id`, `user`, `intent`, `action`, `tool`, sanitized `args`, `decision`, `result_summary`, `outcome`, `duration_ms`; thêm `approval_id`/`operation_id` khi liên quan.
- Phân biệt `decision=allowed|denied|approval_required`, human approval và execution success. Read được policy cho phép không đồng nghĩa đã có người approve.
- Ghi intent audit trước mutation; nếu không ghi được durable record thì không chạy scale. JSON runtime và JSON envelope phục vụ verifier là hai format khác nhau, có bước export rõ ràng.
- Không log raw Slack body, signing secret, bot/provider token, confirmation token, tài liệu hoặc raw exception từ provider. Evidence chỉ chứa bản đã lọc.

## 5. Ma trận yêu cầu và nghiệm thu

| ID | Đầu ra dự kiến | Tiêu chí đạt |
|---|---|---|
| MH1 | `chatops-bot/app/`, `prompts/`, `tests/`, Dockerfile | Cấu trúc đầy đủ, app/worker khởi động được |
| MH2 | FastAPI `/slack/events` và health/readiness | Endpoint thật; health không còn skeleton, readiness báo đúng dependency |
| MH3 | Signature/timestamp validator | Invalid signature 401; valid raw body qua; challenge không bypass auth |
| MH4 | Local bot + cloudflared | HTTPS event URL làm việc trong lượt nghiệm thu |
| MH5 | Slack App config/manifest | Scopes tối thiểu, event subscription và mention/reply thật |
| MH6 | Ba handler và response contracts | Ba câu hỏi chạy trên Slack thật; count đúng mục 3; lỗi dữ liệu không bị che |
| MH7 | Hai MCP connections | Audit/trace từ runtime bot chứng minh call Kubernetes và Prometheus backend thật |
| MH8 | Audit JSONL + sample đã lọc | Truy vết được user -> event -> tool -> decision -> result |
| MH9 | Policy/approval/executor | Read allowed, scale hỏi token, negative cases bị chặn; approved scale dùng identity riêng |
| MH10 | Bot suite + milestone suite + CI | Tests pass, không skip/xfail các scenario bắt buộc; CI có bot job/step |
| MH11 | Screencast 3 phút | Có video thật và URL theo submission, không dùng script/demo notes thay video |
| NFR | ACK/queue/dedup/retry | Đo ACK <3 giây khi LLM chậm, accepted job sống qua worker restart, duplicate không tạo job thứ hai |
| NFR | Identity/secrets/replay | Read SA riêng, mutation SA riêng, token ngoài source và trong Secret, timestamp window được test |

## 6. Trình tự triển khai

| Bước | Công việc | Điều kiện kết thúc |
|---|---|---|
| 1. Chốt baseline/runtime config | Tạo branch `day5-chatops-bot` từ main hiện hành; kiểm dependency, phạm vi cluster/channel và data contract đã chọn | Không diff vào business code; cấu hình local và input live rõ ràng |
| 2. Transport và durable intake | App config, raw signature/timestamp, event filtering, queue/dedup, worker/reply skeleton | HTTP tests và Redis integration chứng minh ACK/recovery trước khi gọi model |
| 3. MCP và ba intents | Config/SA riêng, MCP client, read adapters, deterministic count, response prompt | Cả ba handlers dùng dữ liệu lab thật; MCP trace thật; unit tests dữ liệu thiếu |
| 4. Permissions và audit | Policy, token store, atomic consume, scale executor riêng, JSONL/export | Negative tests chặn đúng; không mutation trước approval |
| 5. Verification và CI | Hoàn thiện bot/milestone tests, dependency pins, bước CI | Hai test suites pass và verifier chạy đúng contract không chỉnh assertions |
| 6. Slack live acceptance | Cấu hình App/cloudflared, mention ba câu, đo ACK, test scale/deny/restore, lưu evidence | Slack replies và scale flow có provenance; runtime không còn tác vụ thay đổi dở |
| 7. Bàn giao | Runbook, review/self-check, prompt log, evidence index, video 3 phút và PR | MH1-MH11 có bằng chứng tương ứng, liệt kê trung thực phần pending |

**Ưu tiên:** transport/reliability trước, ba intent trước, approval/audit sau, nghiệm thu live cuối. Không bắt đầu dựng production hoặc các intent ngoài phạm vi để làm đẹp demo.

## 7. Kiểm thử cần thực hiện

| Nhóm | Positive/negative cases có ý nghĩa |
|---|---|
| Signature | Raw bytes hợp lệ; đổi một byte/parse rồi reserialize; thiếu/sai signature; timestamp malformed, quá khứ/tương lai >300s và boundary; challenge chưa auth bị từ chối |
| Event intake | App/workspace/channel đúng; self/bot event bị bỏ; duplicate/retry đồng thời; queue unavailable; auth failure không gọi model/tool |
| Reliability | LLM chậm nhưng ACK đạt; worker restart sau ACK; enqueue/dedup crash window; retry bounded; Slack 429 và ambiguous send được ghi nhận |
| MCP | Initialize/list/call hai backend; tool/namespace ngoài allowlist; timeout/isError; không trả healthy hoặc count 0 khi thiếu dữ liệu |
| Health/pods | Healthy baseline; missing/stale metrics; pod Running nhưng container lỗi; restart count tích lũy được giải thích đúng |
| Count | Ngày lịch ICT, start inclusive/end exclusive; ready/pending/failed; created hôm trước bị loại; duplicate ID; response truncated/oversized/schema lỗi; không dùng LLM tính số |
| Approval | Ask-confirm; đúng actor/action/params; sai actor/workspace/target/UID/replicas; expired, replay và hai confirms đồng thời; outcome unknown; destructive deny |
| Audit | JSON parse được, đủ correlation, không secrets, audit failure trước mutation, decision khác execution outcome |
| Regression | Smoke upload -> ready -> chat/citations; tests MCP hiện có nếu adapter/config dùng chung bị đổi; verifier regression suite |

### Contract verifier cần đáp ứng nguyên trạng

- `chatops-bot/tests/` là suite sản phẩm theo MH10. Verifier chạy riêng `tests/milestones/day5/test_*.py` từ thư mục tạm, không tự chạy suite bot.
- Milestone suite phải có: `test_permission_denied`, `test_approval_required`, `test_approval_bound_to_action`, `test_duplicate_event`, `test_invalid_signature` cho transport HTTP.
- Tests import bằng `INSIGHTHUB_REPO_ROOT`; tách môi trường/import path để package `app` của bot không bị nhầm với `api/app`. Không copy logic implementation vào tests chỉ để khớp tên.
- Đọc `INSIGHTHUB_VERIFY_RUN_ID`; ghi observation mới vào `INSIGHTHUB_VERIFY_OBSERVATIONS` dạng `{run_id, events}`. Mỗi event có `timestamp`, `event_id`, `action`, `decision`, `user`, `test_run_id`; gồm ít nhất denied và approval_required.
- `docs/evidence/day5/day5.json` có artifact roles `permissions` và `audit`, SHA-256, source fingerprint, observed_at, mode đúng thực tế. Chỉ tạo evidence sau khi source ổn định.
- Audit sample nộp không được bị tests ghi đè; observations của lượt verify nằm ở đường dẫn tạm do verifier cấp.
- HTTP verifier còn kiểm `/healthz`. PASS chỉ bao phủ subset; không tự chứng minh Slack live, count đúng nghiệp vụ, queue durability, hai identities hoặc screencast.
- Unit/CI tests dùng Slack doubles, không gửi tin thật. Lượt nghiệm thu Slack live được thực hiện riêng theo kịch bản và channel đã cấu hình.

Lệnh nghiệm thu dự kiến, chỉ chạy sau khi triển khai:

```bash
python -m pytest chatops-bot/tests/ -v
python -m pytest tests/milestones/day5/ -v
./scripts/verify-day-5.sh \
  --evidence-dir docs/evidence/day5 \
  --bot-transport http \
  --bot-url http://127.0.0.1:8080 \
  --json
```

## 8. File dự kiến tác động

| Vùng | Thay đổi cần thiết |
|---|---|
| `chatops-bot/app/` | main/settings, signature, queue/worker, MCP/read adapters, intents, policy/approval, executor, Slack reply và audit; chia module theo trách nhiệm vừa đủ |
| `chatops-bot/prompts/`, `chatops-bot/tests/` | Prompt ba intent và tests tương ứng |
| `chatops-bot/requirements.in`, `requirements.txt`, Dockerfile, README | Dependencies pin/hashes, runtime instructions và contract count |
| `chatops-bot/config/`, `chatops-bot/deploy/` | Slack manifest/example env không secrets; local SA/RBAC/Secret template và cấu hình chạy tối thiểu |
| `tools/mcp/day5/` | Launch/config cho hai MCP backends đã pin; runtime credentials ở `tmp/day5/` ngoài Git |
| `tests/milestones/day5/` | Năm named scenarios và fresh audit observations theo verifier |
| Makefile, `.github/workflows/starter.yml` | Test/lint/typecheck bot riêng, tích hợp CI tối thiểu; không mở rộng pipeline AWS |
| `docs/day5/`, `docs/evidence/day5/`, `ai-prompts/day5.md` | Runbook, quyết định, self-check, evidence, PR description và prompt log thực tế |
| AGENTS.md/README | Bổ sung context Day 05 và liên kết khi triển khai; giữ giới hạn context hiện có |

Các đường dẫn chưa tồn tại là **deliverables dự kiến**, không phải nội dung đã tạo. Không thay schema/API/worker, không sửa rules/dashboard Day 04 và không đổi verifier.

## 9. Đầu vào live và checklist bàn giao

### Đầu vào kiểm tra khi triển khai

- Slack workspace và channel test; khả năng cấu hình/install App; bot token, signing secret, app/bot user ID; requester/approver allowlist.
- Scopes tối thiểu `app_mentions:read` và `chat:write`; subscribe `app_mention`, invite bot vào channel. Không xin quyền đọc toàn bộ lịch sử workspace. [app_mention](https://docs.slack.dev/reference/events/app_mention/), [chat.postMessage](https://docs.slack.dev/reference/methods/chat.postMessage/).
- Cloudflared URL cho `/slack/events`; endpoint API/Prometheus/Redis local và credential MCP còn hạn. Token Day 04 có thời hạn, không mặc định tái sử dụng được.
- Provider/model cho chatbot từ cấu hình đang có, truy cập được và có khả năng xử lý contract đã chọn. Không đưa API key vào tài liệu.
- Công cụ ghi hình và vị trí lưu video/Loom. Thiếu input nào chỉ để pending acceptance liên quan; không dùng fixture hoặc ảnh nguồn cũ thay bằng chứng.

### Screencast 3 phút

| Thời lượng | Nội dung |
|---|---|
| 0:00-0:20 | Môi trường local, bot đã kết nối, scope ba intent |
| 0:20-1:20 | Hỏi health, ingestion count với nhãn đúng, pods lỗi; chỉ rõ nguồn/thời điểm |
| 1:20-2:15 | Scale API -> approval token -> một negative case -> xác nhận đúng -> kết quả và restore |
| 2:15-3:00 | Audit tương ứng, kết quả tests/verifier và giới hạn kiểm chứng |

### Hoàn thành khi

- [x] Slack live trả lời đủ ba intent, count dùng đúng định nghĩa được trainer chọn.
- [x] Hai MCP backends được runtime bot gọi thật, có audit/correlation; không dùng CLI thay evidence.
- [x] Signature/replay, ACK, queue recovery và duplicate cases được kiểm chứng bằng contract tests.
- [x] Scale không chạy trước approval, dùng identity riêng, deny/replay cases đạt và replica đã restore.
- [x] Bot suite 4/4, milestone suite 6/6, Ruff/Mypy, Docker build, verifier Day 05 và regression smoke PASS. CI job đã thêm, chưa có remote CI run.
- [x] Có runbook, prompt log thực tế và evidence Slack/audit đã lọc.
- [ ] Video 3 phút/URL submission: trainer yêu cầu để sau. Capture đầu ghi nhầm foreground đã loại bỏ.
- [ ] PR/remote CI: `gh` credential hết hạn; remote `main` còn ở Day 03 trong khi local `main` đã merge Day 04, nên PR từ branch hiện tại sẽ mang thêm Day 04 ngoài phạm vi.
- [ ] Dừng tunnel/worker/port-forward sau khi không còn cần chạy video/kiểm tra; không xóa cluster, volumes hoặc tài nguyên Day 04 dùng chung ngoài scope.

**Evidence runtime:** [Day 05 validation](../evidence/day5/Runtime_Validation.md), [audit đã lọc](../evidence/day5/audit.json) và [verifier envelope](../evidence/day5/day5.json). Scope source chỉ là ChatOps/DevOps; không sửa business code hoặc schema ứng dụng.
