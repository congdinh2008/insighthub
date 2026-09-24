# InsightHub - Kế hoạch hoàn thiện Day 04

**Trạng thái cập nhật 24/09/2026:** Core và các lượt real runtime đã có evidence; acceptance còn findings cần đóng theo [review](../day4/Review_and_Self_Check.md).
**Ngày khảo sát:** 23/09/2026. **Lớp:** DO2603.  
**Baseline triển khai:** `main` sau merge Day 03, commit `1dfa6b76ceca5e1e659545c535ad3c3266f495a2`.  
**Branch triển khai dự kiến:** `day4-observability`.  
**Mục tiêu:** Hoàn thiện MH1-MH10, MH12, các functional/non-functional acceptance Day 04 và evidence tương ứng, đạt rubric L3. MH11 (quiz) do trainer phụ trách, đã loại khỏi phạm vi triển khai.

## 1. Nguồn yêu cầu và giới hạn phạm vi

Thứ tự đối chiếu:

1. [Specification v3.3, mục 0, 4, 8](../../Running-Project-Specification-Student.md): nguồn yêu cầu chính.
2. [Lab Day 04](../lab-guides/Day4-AIOps-Observability.md) và [guide local/AWS](../Guide_Local_AWS_Cost_DO2603.md): cách tổ chức và vận hành lab.
3. [Verification contract](../../scripts/VERIFICATION_CONTRACT.md) và [verifier](../../scripts/verify.py): contract artifact và phần tự động kiểm được.
4. [AGENTS.md](../../AGENTS.md), source Day 01-03 và evidence Day 03: baseline triển khai.
5. [Học liệu Day 04 ngày 17/09/2026](<../../../9. AI for Devops/06_Customize/DO2603/03_HocLieu/Day04_KienThuc_ThucHanh_20260917/Day04_KienThuc_ThucHanh_AIOps_MLOps_InsightHub_v1.0.md>): tham khảo metric semantics, baseline, RCA và cấu trúc notes; không nhập toàn bộ bài mở rộng vào scope.

**Trong phạm vi:** ServiceMonitor/exporters đủ năm thành phần, một dashboard có chín query panels, recording/anomaly rules cho ba tín hiệu, Alertmanager tới Slack thật, ba incident với baseline/failure/recovery và AI RCA, MLOps overview notes, prompt log, kiểm thử và tài liệu tái lập. Quiz do trainer phụ trách.

**Không đưa vào kế hoạch:** Grafana Sift/Pro, routing nâng cao theo severity, Adaptive Telemetry/tail sampling/log filtering, SLO/burn-rate alerts, runbook riêng từng alert, knowledge graph, auto-postmortem, chaos engineering platform, dashboard chi phí monitoring stack. Đây là Should-have/Nice-to-have, không cần để đạt L3. Ba script inject incident tối thiểu vẫn là bắt buộc.

Không triển khai Slack ChatOps bot, autonomous remediation, LiteLLM, Promptfoo hoặc Day 05-06. MLOps chỉ notes, không dựng MLflow, registry server, training/retraining hoặc serving pipeline. Không đổi schema, embedding identity, layout web hay business feature.

Plan này đã được dùng làm baseline triển khai trên branch `day4-observability`. Runtime evidence chỉ được ghi khi quan sát thật; các gate thiếu provider, Slack hoặc thời lượng baseline giữ trạng thái pending.

## 2. Hiện trạng và gap đã xác định

| Hạng mục | Hiện trạng có căn cứ | Công việc Day 04 |
|---|---|---|
| Git | Checkout sạch trước khi tạo plan; `day3-terraform` tại `06ae666`; `main` local vẫn tại `ee6e168` của Day 02 | Tạo branch nối tiếp Day 03; chọn PR base theo tình trạng merge khi bắt đầu |
| Deployment | Helm có web/api/worker Deployments và PostgreSQL/Redis local; API và worker có Service với named port | Tái sử dụng chart, namespace `insighthub-dev`; bổ sung monitoring opt-in |
| API metrics | Có HTTP request counter, RAG/LLM latency histogram, token counters, document status gauge | Thêm HTTP duration histogram để RED bao phủ API; chỉ bổ sung nhãn model nếu cần phân biệt đơn giá, giữ cardinality hữu hạn |
| Worker metrics | Có job outcomes/duration và endpoint nội bộ `:8081/metrics` | Scrape trực tiếp; tái sử dụng, không viết lại worker |
| Queue | ARQ sử dụng Redis sorted set; chưa có queue depth metric | Lấy kích thước đúng queue từ Redis exporter, độc lập với worker |
| Local AI mode | `values-local.yaml` dùng fixture; generation fixture không trả token usage | Chuẩn bị workload real provider có usage để nghiệm thu token/cost và latency |
| Monitoring | `observability/` mới có README; Prometheus Day 02 chỉ scrape API/worker bằng static targets | Cấu hình kube-prometheus-stack, ServiceMonitor/exporters, dashboard/rules/Slack |
| MCP | Kubernetes backend Day 02 giới hạn namespace `insighthub`; Prometheus trỏ lab Day 02 | Tạo cấu hình phiên lab Day 04 trỏ `insighthub-dev` và Prometheus mới, giữ quyền đọc |
| AWS | Evidence Day 03 ghi deploy, E2E và cleanup hoàn tất | Day 04 chạy local theo mục 0.2; không provision lại AWS để lấy dashboard |
| Verifier | Kiểm chín query panels, rules/tests, ba RCA khác ID, citations khớp Prometheus | Chuẩn bị đúng artifact contract; kiểm thủ công các acceptance verifier chưa bao phủ |

Đây là khảo sát source và hồ sơ đã lưu. Chưa xác minh runtime hiện tại, chưa khẳng định Prometheus/Grafana/Slack hoặc Day 04 đã chạy.

## 3. Quyết định triển khai vừa đủ

### 3.1. Môi trường và topology

- Dùng Kubernetes local và chart Day 03. Application namespace giữ `insighthub-dev`; monitoring namespace `monitoring`. Không đổi sang `insighthub` chỉ để khớp câu lệnh ví dụ trong spec.
- Nếu cluster Day 03 đang được anh dùng kiểm tra, dựng lab local riêng từ cùng chart để inject fault. Chỉ lab được xác định mới được thay replicas hoặc route provider.
- Dùng kube-prometheus-stack cho Operator, Prometheus, Alertmanager, Grafana và kube-state-metrics; tận dụng kubelet/cAdvisor cho tài nguyên pod. Pin chart/images tương thích phiên bản Kubernetes tại bước setup, không mặc định dùng latest.
- Prometheus retention **15d**, có persistent storage và requests/limits. Chọn dung lượng/PVC sau kiểm tra storage class và tài nguyên local; kiểm tra render/rollout. Không hạ retention để che lỗi thiếu tài nguyên.
- Scrape/evaluation dự kiến 30s, normalization/anomaly recording interval 1m. Đặt resource requests/limits trước khi chạy baseline.
- Grafana local là giao diện nghiệm thu. Grafana Cloud account ở pre-class không đồng nghĩa phải triển khai remote-write hoặc mua Pro; mục 0.2 và guide cho phép baseline/telemetry local.
- Port-forward chỉ loopback. Không thêm public endpoint hoặc AWS telemetry service.

| Thành phần | Tín hiệu tối thiểu và nguồn |
|---|---|
| Web | Availability/replicas/restarts và CPU/RAM qua kube-state-metrics/kubelet; HTTP UI smoke qua browser |
| API | Request rate, 5xx ratio, HTTP/RAG duration, LLM p95, usage từ `/metrics` |
| ingestion-worker | Job outcomes/duration, pod health/resources từ worker `/metrics` và Kubernetes |
| PostgreSQL | `pg_up`, connections/activity qua PostgreSQL exporter, credential giám sát giới hạn |
| Redis | `redis_up`, memory/clients và đúng queue key size qua Redis exporter |

Năm thành phần không yêu cầu năm endpoint `/metrics` tự viết. Web có tín hiệu workload thật từ Kubernetes. ServiceMonitor dùng named Service ports; Prometheus selectors phải chọn đúng labels và namespaces. Đối chiếu [Prometheus Operator](https://prometheus-operator.dev/docs/platform/troubleshooting/).

### 3.2. Metric contract cần chốt trước dashboard

1. **HTTP:** thêm histogram thời gian xử lý request với route template/method và buckets phù hợp. Lọc `/metrics`, `/healthz`, `/readyz` khỏi business RED queries; lỗi nghiệp vụ 4xx không trộn thành server 5xx anomaly.
2. **Queue:** đọc sorted-set cardinality của `queue_name` đang cấu hình, không dùng `LLEN`, tổng số Redis keys hoặc số document pending thay queue depth. ARQ version hiện tại giữ cả một số job đang chạy/deferred trong set, nên tên/description phải ghi rõ là outstanding queue entries. Không khẳng định đây là số job đang chờ thuần túy.
3. **Collector độc lập worker:** worker có thể scale về 0 ở incident backlog; Redis exporter vẫn phải báo được queue. Dùng `check-single-keys` với đúng key, không quét toàn keyspace. Empty queue chỉ được biểu diễn 0 khi xác minh key không tồn tại nhưng Redis/collector đang khỏe; lỗi/mất scrape phải giữ trạng thái unknown. [Redis exporter](https://github.com/oliver006/redis_exporter).
4. **Latency:** LLM p95 lấy từ histogram generation, tách RAG end-to-end và HTTP duration. Không dùng trung bình thay p95; có sample-volume guard.
5. **Token/cost:** dùng provider-reported usage. Cost panel là **ước tính phí LLM generation API**, dựa trên model và đơn giá có nguồn/ngày; không gọi là billing tổng, không gồm hạ tầng hoặc embedding. Giữ một model/đơn giá trong lượt đo hoặc bổ sung nhãn model hữu hạn để tránh trộn giá. Không dùng word-based estimate hoặc fixture làm token thật.
6. **Deployment:** dùng Deployment generation/observed generation từ Kubernetes cho query panel, cùng Grafana annotation tại rollout thực có revision/image/timestamp. Không thêm release pipeline mới.

### 3.3. Dashboard đúng chín panel

| # | Panel | Query/data và điều kiện review |
|---|---|---|
| 1 | Request rate | HTTP counter rate theo business route; chứng minh load vào API |
| 2 | Error rate | 5xx/business requests; zero 5xx chỉ hợp lệ khi request counter đang được scrape và có traffic |
| 3 | Duration | HTTP duration và RAG end-to-end, units giây rõ ràng |
| 4 | Queue depth | Recorded outstanding queue entries và anomaly band; tăng khi worker dừng, giảm khi khôi phục |
| 5 | Token usage | Input/output generation usage thật, model/provider rõ ràng |
| 6 | LLM latency p95 | p95, baseline, upper/lower bands và trạng thái anomaly |
| 7 | Estimated generation API cost | Usage × đơn giá, USD; ghi phạm vi và nguồn giá |
| 8 | Pod resources/health | CPU/RAM/readiness/restarts cho năm thành phần local; kèm tín hiệu DB/cache health để review coverage |
| 9 | Deployment history | Query generation/observed generation, annotation rollout thật và revision |

Mỗi panel có `targets[].expr` thực. Annotation-only panel không đáp ứng contract verifier. Khi nghiệm thu, chọn khoảng thời gian có workload/rollout thật, không còn `No data`; không thêm `or vector(0)` đại trà để che metric thiếu.

### 3.4. Anomaly rules và baseline

- Một file canonical `observability/chart/files/anomaly-rules.yaml` chứa normalization, mean/stddev/bands, volume/warmup guards và đúng ba anomaly alerts: LLM latency, queue backlog, server error ratio.
- Dùng PromQL statistical bands theo hướng [grafana/promql-anomaly-detection](https://github.com/grafana/promql-anomaly-detection), với lab windows được ghi rõ. Không cài nguyên adaptive defaults cần history dài rồi tuyên bố đủ bằng một giờ dữ liệu.
- Thiết kế lab dự kiến: baseline window **1h**, offset **10m**, recording interval **1m**, alert `for: 2m`. Sigma/impact floors có units và được review theo workload, trước khi inject lỗi.
- Cần ít nhất **70 phút recorded history**, thực tế nên dự trù 75 phút để tránh biên thời gian; raw history có trước không tự backfill recording series mới. Bắt đầu tích lũy sau khi metric contract/rules đã ổn định.
- Có guard cho đủ span/mẫu, scrape health, lượng request/calls và giá trị finite. Missing/NaN/no traffic không coi là healthy. Baseline ít variance cần sigma floor.
- Mỗi incident dùng baseline sạch của chính metric. Sau recovery, chờ cửa sổ baseline sạch lại nếu bị nhiễm; không chỉnh threshold sau lỗi chỉ để có PASS.
- LLM incident phải fire trong **5 phút** tính từ thời điểm inject đã ghi. Rehearsal mức delay/load và cửa sổ query trước lần nghiệm thu để đạt mốc này; ghi cả firing latency và Slack delivery latency thực đo.
- Production baseline ≥7 ngày là kiến thức/non-functional định hướng trong spec, không yêu cầu giữ lab chạy bảy ngày.

Kiểm tests có ý nghĩa: normal, sustained incident, short spike, recovery cho cả ba tín hiệu; warmup thiếu, sigma=0, no traffic, absent 5xx, missing scrape và counter reset. `promtool check rules` và `promtool test rules` chạy trên đúng file canonical. Manifest PrometheusRule lấy cùng `groups` từ file đó, tránh hai bản rules lệch nhau.

### 3.5. Slack và ba incident/RCA

Alertmanager dùng một receiver tới Slack `#alerts`, có firing/resolved và grouping tối thiểu để tránh lặp. Webhook được mount từ Secret, không ghi vào Git hoặc evidence; cấu hình file secret theo [Alertmanager Slack configuration](https://prometheus.io/docs/alerting/latest/configuration/#slack_config). Chỉ test notification khi đã xác định đúng workspace/channel và được anh cho phép gửi ở bước triển khai.

| Incident | Cơ chế lỗi trong lab | Khôi phục và tín hiệu phải ghi |
|---|---|---|
| #1 LLM latency spike | Proxy lab trên endpoint OpenAI-compatible đã được adapter hỗ trợ, chỉ delay generation request trước khi forward tới provider thật; giữ timeout hữu hạn | Bỏ delay; LLM p95 giảm, request tiếp tục thành công, anomaly fire ≤5 phút và resolved |
| #2 Queue backlog | Tạm scale đúng worker Deployment về 0, upload số lượng tài liệu mẫu có giới hạn để queue tăng | Khôi phục replicas ban đầu; queue drain, documents ready, worker completion tăng |
| #3 Error burst | Proxy lab trả 503 có kiểm soát trên generation requests, đi qua xử lý lỗi API thật; không dùng request validation 4xx | Tắt fault; 5xx ratio về baseline, chat thành công và alert resolved |

Proxy chỉ phục vụ hai chế độ fault của bài tập, không xây gateway/model routing platform. Các lượt bình thường dùng model thật với token usage; response lỗi được inject và ghi rõ nguồn. Không dùng mock telemetry/RCA soạn sẵn thay runtime evidence. Embedding provider/model/index giữ nguyên identity đã chọn cho lab, không đổi trực tiếp trên dữ liệu cũ.

Mỗi script yêu cầu context/namespace/label lab cụ thể, ghi initial state và timestamps, giới hạn load/thời gian, có cleanup/restore khi kết thúc hoặc bị ngắt. Chạy tuần tự từng incident, kiểm baseline trước và recovery sau. Không thao tác cluster/service của lab khác.

**AI RCA workflow:** Codex gọi Prometheus MCP và Kubernetes MCP thật với quyền đọc; lấy query range, pod status/events/logs giới hạn; tách observed/inferred/unknown; nêu giả thuyết và phép kiểm phân biệt; review đối chiếu telemetry rồi hoàn thiện JSON. Operator thực thi rollback, AI RCA không tự mutation.

MCP Day 04 tái sử dụng backend/pin Day 02, thay endpoint và namespace bằng cấu hình phiên lab. ServiceAccount/RBAC chỉ đọc đúng namespace; không cấp quyền đọc Secrets hoặc cluster-admin. Không dùng CLI output thay bằng chứng host MCP calls.

Mỗi `rca-reports/incident-N.json` có tối thiểu `incident_id`, `started_at`, `ended_at`, `hypotheses`, `samples[{metric,labels,timestamp,value}]` đúng verifier. Bổ sung environment/source commit, query/time range, observations, root-cause assessment, confidence có căn cứ, uncertainty, action thực hiện và recovery evidence. Không ép confidence >0.7 nếu dữ kiện chưa đủ. Metric citations dùng metric name/recorded series, không nhét biểu thức PromQL vào trường `metric`; query expression lưu riêng.

## 4. Ma trận yêu cầu và nghiệm thu

| ID | Đầu ra | Điều kiện nghiệm thu |
|---|---|---|
| MH1 | ServiceMonitor manifests | Applied đúng namespace/selectors/named ports; Prometheus thực sự discover |
| MH2 | Coverage năm thành phần | Targets dự kiến UP ở baseline/final recovery; query có dữ liệu cho từng thành phần, không chỉ đếm targets |
| MH3 | Dashboard JSON/URL/screenshots | Chín query panels đúng nội dung, no No data trên khoảng nghiệm thu |
| MH4 | Recording rules + PrometheusRule | Resource có thật, rules loaded/evaluation không lỗi, bands có dữ liệu |
| MH5 | Ba anomaly alerts + rule tests | promtool check/test PASS; normal/failure/recovery đúng kỳ vọng |
| MH6 | Alertmanager config + Slack evidence | Test alert và incident alerts tới đúng `#alerts`; lưu timestamp/permalink hoặc ảnh đã che thông tin nhạy cảm |
| MH7 | `incident-1.json` | Latency fault thật, fire ≤5 phút, MCP analysis và recovery |
| MH8 | `incident-2.json` | Backlog thật, alert fire, worker restored, queue drain |
| MH9 | `incident-3.json` | Server error burst thật, alert fire, chat hoạt động lại |
| MH10 | Citations trong cả ba RCA | Metric/labels/value/timestamp khớp query Prometheus, suy luận được review |
| MH11 | Quiz | Ngoài phạm vi triển khai theo trainer; không tạo điểm hoặc nộp form |
| MH12 | `mlops-overview-notes.md` | Đủ bốn block, trả lời được self-check, không gọi notes là implementation |
| NFR | Baseline/storage/resources | Recorded baseline ≥1h hợp lệ trước lỗi; retention 15d; limits; expensive query qua recording rules |
| Submission | Prompt log/source/PR/evidence | Conventional Commits, branch đúng, AI workflow và kết quả thực kiểm được |

**Quiz:** Trainer đã loại khỏi phạm vi triển khai; tài liệu practice chỉ là tham khảo, không thay điểm lớp. Verifier PASS không tự chứng minh Slack delivery, causality của RCA, panel semantics hoặc MLOps understanding.

**Bốn block MLOps notes:** (1) App artifact so với model artifact; (2) ML lifecycle và ownership DevOps/ML; (3) Registry, Approval Gate, Data/Concept Drift, Rollback; (4) case release decision và bằng chứng cần có. DevOps vận hành pipeline được giao, không tự quyết định retrain/promote ngoài ownership. Notes liên hệ InsightHub nhưng không thêm model feature.

## 5. Trình tự triển khai sau khi review

| Bước | Việc thực hiện | Kết quả/gate chuyển bước |
|---|---|---|
| 1. Chốt baseline | Xác minh repo/Day 03 ancestry; tạo `day4-observability`; chọn lab context, real provider và đầu vào Slack | Branch từ code Day 03; lab và acceptance rõ ràng, không dựa `main` local đang thiếu Day 03 |
| 2. Instrument/scrape | Bổ sung HTTP duration tối thiểu; cấu hình stack/exporters/ServiceMonitor/storage/limits; MCP lab config | Năm thành phần có tín hiệu, model thật trả usage, application smoke PASS |
| 3. Rules/dashboard | Hoàn thiện canonical rules + tests, render PrometheusRule, provision chín panels/annotations/receiver | Static/rule tests PASS, loaded rules đúng, metric/query review xong |
| 4. Baseline | Chạy workload ổn định có giới hạn, thu recorded history dự kiến ≥75 phút; làm notes/prompt documentation trong thời gian chờ | Warmup/span/sample-count/volume guards đủ, không có false firing không giải thích được |
| 5. Incident/RCA | Test Slack rồi chạy ba incident tuần tự, MCP query/review, restore sau mỗi incident | Ba bộ baseline/failure/recovery, alerts thật, RCA citations chính xác |
| 6. Nghiệm thu | Browser E2E, verifier Day 04, regression phù hợp diff; review notes/prompt log | Ma trận MH/NFR có trạng thái và evidence rõ, không bỏ qua integration pending |
| 7. Bàn giao | Runbook, self-check, evidence index, commits và PR Day 04; kết thúc fault/load, cleanup lab được tạo cho lượt này sau kiểm chứng | Source tái lập, dữ liệu nghiệm thu đã lưu, không còn fault/traffic generator chạy |

Các bước 2-3 phải ổn định trước giờ baseline. Có thể hoàn thiện notes và tài liệu trong thời gian thu baseline, nhưng không thay rules/model/labels làm mất tính liên tục. Tổng thời gian thực tế gồm setup/test và ít nhất một lượt warmup; không coi lab 50 phút trên lớp là đủ toàn bộ yêu cầu.

### Prompt workflow dự kiến

`ai-prompts/day4.md` là nhật ký ba prompt lịch sử đã dịch, có giới hạn provenance ghi rõ. `ai-prompts/day4-templates.md` là bộ prompt tiếng Việt chuẩn hóa để sử dụng tiếp. Không ghi prompt pack mới thành lịch sử đã dùng. Mỗi entry thực thi cần host/version/model/auth mode có căn cứ, timestamp, context/evidence, prompt constraint-first, lý do hiệu quả và điều người học review/chỉnh. Dùng `prompts/rca-template.md` cho bước điều tra từng incident.

1. Khảo sát kiến trúc và mapping requirement/gap.
2. Lập plan; scope review và chốt lựa chọn vừa đủ.
3. Metric/exporter/dashboard implementation và review semantics.
4. Anomaly rules, baseline và test design/review.
5. Evidence-first RCA cho từng incident, có actual MCP calls.
6. Review chéo RCA, chạy kiểm thử, tự đối chiếu acceptance và MLOps notes.

Đáp ứng tối thiểu ba prompts theo mục 4.4; quy trình đi từ hiểu kiến trúc đến planning/review, implementation và verification.

## 6. File và commit dự kiến

| Vị trí | Nội dung |
|---|---|
| `observability/` | README, values stack/exporters, manifests/ServiceMonitor, canonical anomaly rules/tests, generated PrometheusRule và dashboard JSON |
| `deploy/helm/insighthub/` | Thay đổi opt-in tối thiểu phục vụ monitoring/lab; giữ deployment Day 03 hoạt động khi không bật |
| `api/app/core/metrics.py`, `api/app/main.py` và tests liên quan | HTTP duration và usage identity nếu cần; giữ contract upload/chat |
| `scripts/chaos/` | Ba script inject/restore và helper/proxy lab tối thiểu |
| `tools/mcp/` | Cấu hình endpoint/namespace Day 04 tái sử dụng backend hiện có, không thay pin tùy tiện |
| `rca-reports/incident-1.json` tới `incident-3.json` | Ba báo cáo incident có citations runtime |
| `mlops-overview-notes.md`, `ai-prompts/day4.md`, `ai-prompts/day4-templates.md`, `prompts/rca-template.md` | Notes bốn block, nhật ký prompt, bộ prompt tiếng Việt để dùng tiếp và mẫu RCA |
| `docs/day4/` | Runbook, metric contract, self-check/acceptance, quiz status và PR description |
| `docs/evidence/day4/` | Manifest, rule/verification output, MCP traces đã lọc, baseline/incident/recovery và browser/Slack evidence |

Không sửa specification hoặc verifier/assertions để phù hợp bài làm. Cập nhật AGENTS.md chỉ phần context Day 04 cần thiết khi triển khai, giữ sáu section và ≤200 dòng.

Commit dự kiến theo phần việc:

1. `docs(day4): define observability scope and acceptance plan`
2. `feat(observability): collect InsightHub service and queue metrics`
3. `feat(observability): add RED dashboard and anomaly alerting`
4. `test(observability): add bounded incident scenarios and rule coverage`
5. `docs(day4): add verified RCA evidence and MLOps overview`

PR title: `[Day 4] Add InsightHub observability and evidence-based incident RCA`. Nếu Day 03 chưa vào `main`, dùng PR base `day3-terraform` để diff chỉ chứa Day 04; khi Day 03 đã merge, dùng `main` sau khi xác minh ancestry. Không tự merge PR.

## 7. Kiểm thử và evidence contract

- **Static:** Helm lint/template; kiểm selectors, limits, retention, secret references và query expressions; promtool check/test canonical rules. Lint/typecheck/backend tests đúng phần code sửa.
- **Runtime:** targets/loaded rules, đủ năm thành phần; usage/cost provenance; baseline guards; từng incident pending/firing/resolved, Slack delivery, recovery thật. Target mất do worker scale 0 là lỗi inject có chủ đích, phải UP lại sau restore.
- **Regression:** upload 202, worker xử lý tài liệu, chat/citations; smoke chart khi monitoring tắt; chỉ mở rộng regression khi diff/rủi ro hoặc failure yêu cầu.
- **Browser E2E bằng Computer Use:** mở Grafana, chọn đúng time range, kiểm chín panels/annotations; kiểm Alertmanager và Slack evidence; sau recovery mở InsightHub upload/chat/citations. Lưu ảnh có timestamp, không chỉ dựa screenshot dashboard JSON import thành công.
- **RCA evidence:** đủ source/commit/context/time range/query/raw response đã lọc và host MCP trace. Lưu samples đúng output query, không làm tròn hoặc nhập thủ công số liệu làm lệch verifier.

`docs/evidence/day4/day4.json` phải theo schema verifier hiện có: `schema_version`, `day: 4`, `mode`, `observed_at`, `source_sha256`, `artifacts`. Mỗi artifact có repository-relative `path` và `sha256`. Roles bắt buộc: `rca`, `rca_2`, `rca_3`, `rules`, `rule_tests`, `dashboard`, `mlops_notes`.

Sau khi source và artifacts ổn định, tạo hashes từ files thực rồi chạy:

```bash
./scripts/verify-day-4.sh \
  --evidence-dir docs/evidence/day4 \
  --prometheus-url "$DAY4_PROMETHEUS_URL" \
  --json
```

`DAY4_PROMETHEUS_URL` là endpoint local thực đã xác minh. Rule tests phải trỏ đúng submitted rule file. Prometheus phải còn giữ samples của cả ba incident lúc verifier chạy; mặc định evidence freshness là 24 giờ. Chạy trước cleanup, lưu report với timestamp; evidence cũ là hồ sơ lịch sử, không tự nhận là vừa được runtime-verify lại. Thay source sau nghiệm thu phải cập nhật evidence binding và kiểm lại phần liên quan.

Source fingerprint đã bao phủ `observability/`, `tools/` và `scripts/`, nhưng chưa quét `deploy/` và `rca-reports/`. Ba RCA được kiểm qua artifact hashes đã khai báo. Bổ sung hash/index cho rendered deployment manifests trong evidence bàn giao, không tuyên bố verifier tự xác minh toàn bộ deployment.

## 8. Đầu vào và điểm cần theo dõi

| Đầu vào/khác biệt | Cách xử lý trong plan |
|---|---|
| Slack workspace, `#alerts`, incoming webhook và quyền gửi test | Chốt trước bước notification; không yêu cầu paste secret vào hội thoại. Thiếu thì MH6 pending, không thay bằng webhook mock |
| Real provider/model có usage, credential và hạn mức workload | Dùng adapter sẵn có, ưu tiên OpenAI-compatible cho lab proxy; xác minh cấu hình và đơn giá trước run. Không thêm provider integration mới |
| Embedding/index | Tái sử dụng identity phù hợp; nếu cần real dataset mới thì tạo lab dataset/index tách biệt, không đổi identity tại chỗ |
| Local capacity/storage | Kiểm trước install, chọn requests/limits/PVC tương ứng; giữ retention 15d |
| Quiz form/kết quả chính thức | Trainer phụ trách, ngoài phạm vi triển khai |
| Namespace spec `insighthub` so với chart `insighthub-dev` | Dùng namespace chart hiện tại nhất quán và ghi mapping trong runbook/evidence |
| Baseline ≥1h so với window 1h offset 10m | Thu ít nhất 70 phút recorded history, dự trù 75 phút; không hạ window cho kịp demo |
| 9 panels so với 9 query panels | Panel deployment có query thực và annotations; không dùng annotation-only để đếm đủ |

**Điều kiện kết thúc:** hoàn tất MH1-MH10, MH12 và NFR/submission tương ứng, ba incident có evidence thật, smoke sau recovery PASS, không còn fault hoặc load generator. Mục còn thiếu đầu vào/runtime evidence phải ghi pending; MH11 ngoài phạm vi. Không công bố hoàn tất Day 04 chỉ vì verifier PASS. Evidence đã triển khai ở `docs/evidence/day4/incident-*.json`, khác đường dẫn dự kiến ban đầu `rca-reports/incident-N.json`; manifest ánh xạ ba file thực.
