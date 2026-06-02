# Hướng dẫn cài đặt & cấu hình Prometheus + Grafana cho InsightHub

> **Đối tượng:** Học viên (standalone — tự làm không cần mentor)
> **Branch:** `day4-aiops`
> **Pre-requisite:** Cluster Kubernetes đang chạy (kind/minikube/EKS), `kubectl` + `helm` đã cài, InsightHub đã deploy (5 pods `Running` trong namespace `insighthub-dev`).
> **Quan hệ với tài liệu khác:**
> - Tài liệu này = **khái niệm + cài đặt từng bước có giải thích** (đứng một mình).
> - [`DAY_04_README.md`](../../DAY_04_README.md) = kịch bản buổi học của mentor (inject incident + AI RCA + MLOps). Đọc sau khi hoàn tất guide này.
> - Các file cấu hình thật nằm trong [`observability/`](../../observability/).

---

## Mục lục

1. [Phần A — Prometheus & Grafana là gì?](#phần-a--prometheus--grafana-là-gì)
2. [Phần B — Vai trò trong dự án InsightHub](#phần-b--vai-trò-trong-dự-án-insighthub)
3. [Phần C — Kiến trúc observability InsightHub](#phần-c--kiến-trúc-observability-insighthub)
4. [Bước 0 — Chuẩn bị & kiểm tra điều kiện](#bước-0--chuẩn-bị--kiểm-tra-điều-kiện)
5. [Bước 1 — Cài kube-prometheus-stack](#bước-1--cài-kube-prometheus-stack)
6. [Bước 2 — Xác minh API có export /metrics](#bước-2--xác-minh-api-có-export-metrics)
7. [Bước 3 — ServiceMonitor: cho Prometheus scrape InsightHub](#bước-3--servicemonitor-cho-prometheus-scrape-insighthub)
8. [Bước 4 — PrometheusRule: recording + alert rules](#bước-4--prometheusrule-recording--alert-rules)
9. [Bước 5 — Truy cập Grafana & cấu hình datasource](#bước-5--truy-cập-grafana--cấu-hình-datasource)
10. [Bước 6 — Import dashboard InsightHub](#bước-6--import-dashboard-insighthub)
11. [Bước 7 — Alertmanager → Slack](#bước-7--alertmanager--slack)
12. [Bước 8 — Verify toàn bộ stack](#bước-8--verify-toàn-bộ-stack)
13. [Phụ lục — Troubleshooting](#phụ-lục--troubleshooting)

---

## Phần A — Prometheus & Grafana là gì?

### Prometheus — "bộ thu thập số liệu" (metrics)

**Prometheus** là hệ thống **giám sát (monitoring)** và **time-series database** mã nguồn mở (gốc từ SoundCloud, nay thuộc CNCF — cùng nhà với Kubernetes). Cơ chế cốt lõi:

| Khái niệm | Giải thích | Trong InsightHub |
|---|---|---|
| **Metric** | Một con số đo theo thời gian (vd: số request, độ trễ) | `insighthub_llm_call_latency_seconds`, `insighthub_ingestion_queue_depth` |
| **Pull model** | Prometheus **chủ động "cào" (scrape)** endpoint `/metrics` của ứng dụng theo chu kỳ | Scrape `api:8000/metrics` mỗi 30s |
| **Exporter / instrumentation** | Code trong app phơi bày metric ra `/metrics` | Thư viện `prometheus-client` trong `api/app/core/metrics.py` |
| **PromQL** | Ngôn ngữ truy vấn metric | `rate(insighthub_http_requests_total[5m])` |
| **Recording rule** | Tính sẵn 1 biểu thức phức tạp thành metric mới | `job:insighthub_llm_latency_upper_band` |
| **Alert rule** | Điều kiện → bắn cảnh báo | `InsightHubErrorRateAnomaly` khi 5xx > 5% |

**Điểm mấu chốt:** Prometheus dùng **pull model** — nó tự gọi đến app, chứ app không đẩy số liệu đi. Vì vậy app chỉ cần phơi bày `/metrics`, còn Prometheus lo phần thu thập, lưu trữ, và truy vấn.

```
┌──────────────┐   scrape mỗi 30s    ┌────────────┐   PromQL    ┌─────────┐
│ InsightHub   │ ◄────────────────── │ Prometheus │ ◄────────── │ Grafana │
│ api /metrics │                     │  (TSDB)    │             │         │
└──────────────┘                     └────────────┘             └─────────┘
```

### Grafana — "bảng điều khiển trực quan" (visualization)

**Grafana** là nền tảng **trực quan hóa & dashboard** mã nguồn mở. Bản thân Grafana **không lưu metric** — nó **đọc dữ liệu từ datasource** (ở đây là Prometheus) và vẽ thành biểu đồ, gauge, bảng, alert.

| Khái niệm | Giải thích |
|---|---|
| **Datasource** | Nguồn dữ liệu Grafana kết nối tới (Prometheus, Loki, CloudWatch...) |
| **Dashboard** | Tập hợp panel hiển thị | 
| **Panel** | 1 biểu đồ/đồng hồ chạy 1 truy vấn PromQL |
| **Variable** | Biến để lọc dashboard động (vd: chọn pod, namespace) |

**Phân vai một câu:** **Prometheus thu thập & lưu số liệu; Grafana biến số liệu đó thành hình ảnh để con người nhìn ra vấn đề.** Hai công cụ này gần như luôn đi đôi với nhau.

### Tại sao đi cùng nhau? Vòng đời một metric

```
1. app instrument   → metrics.py định nghĩa insighthub_llm_call_latency_seconds
2. app phơi bày     → GET /metrics trả về text format Prometheus
3. Prometheus scrape→ ServiceMonitor bảo Prometheus cào api:8000/metrics mỗi 30s
4. Prometheus lưu   → TSDB giữ 15 ngày
5. Recording rule   → tính baseline + 3σ → upper_band
6. Alert rule       → latency > upper_band trong 2m → fire alert
7. Alertmanager     → route alert → Slack #insighthub-alerts
8. Grafana          → vẽ chart latency + đường upper_band để mắt thường thấy spike
```

---

## Phần B — Vai trò trong dự án InsightHub

InsightHub là **RAG Notebook** (giống Google NotebookLM): upload tài liệu → chunk + embed → pgvector → hỏi đáp bằng LLM. Hệ có 5 service: `web`, `api`, `ingestion-worker`, `postgres`, `redis`.

**Vấn đề Day 3 để lại:** App đã LIVE trên K8s, nhưng khi user báo *"đôi khi chậm"*, đội vận hành **không biết khi nào, ở đâu, tại sao**. Không có số liệu → mọi chẩn đoán là phỏng đoán.

**Prometheus + Grafana giải quyết gì cho InsightHub:**

| Câu hỏi vận hành | Metric InsightHub trả lời | Công cụ |
|---|---|---|
| "LLM có đang chậm bất thường không?" | `insighthub_llm_call_latency_seconds` | Prometheus histogram + Grafana chart |
| "Tài liệu upload bị kẹt ở đâu?" | `insighthub_ingestion_queue_depth` | Gauge — queue backlog |
| "Có bao nhiêu % request lỗi?" | `insighthub_http_requests_total{status=~"5.."}` | Recording rule error rate |
| "Truy vấn RAG p95 mất bao lâu?" | `insighthub_rag_query_latency_seconds` | `histogram_quantile(0.95, ...)` |
| "Tốn bao nhiêu token LLM?" (Day 6 FinOps) | `insighthub_llm_tokens_total{direction}` | Counter |

**Giá trị cốt lõi — rút ngắn MTTR (Mean Time To Resolution):**

- **Không có observability:** mở log thủ công, đoán → ~25 phút mới tìm ra nguyên nhân.
- **Có Prometheus + Grafana + alert:** anomaly bắn cảnh báo **trước khi user phàn nàn**; AI agent query Prometheus (qua MCP) trả RCA trong ~2 phút → tổng MTTR ~7 phút.

> Đây chính là bước chuyển từ *"chờ user báo lỗi"* sang *"I can see what's broken before users complain"* — mục tiêu Day 4.

Những metric này còn là **nền tảng cho các Day sau**: token counter phục vụ **FinOps Day 6**; alert + RCA phục vụ **AI incident response**.

---

## Phần C — Kiến trúc observability InsightHub

```
                          namespace: monitoring
   ┌─────────────────────────────────────────────────────────────┐
   │  kube-prometheus-stack (Helm release: kube-prom-stack)        │
   │                                                               │
   │   ┌────────────┐   ┌──────────────┐   ┌─────────────────┐    │
   │   │ Prometheus │   │   Grafana    │   │  Alertmanager   │    │
   │   │  :9090     │   │   :80        │   │   :9093         │    │
   │   └─────▲──────┘   └──────▲───────┘   └────────▲────────┘    │
   │         │ scrape          │ query              │ route        │
   └─────────┼─────────────────┼────────────────────┼─────────────┘
             │                 │                     │
   ══════════╪═════════════════╪═════════════════════╪═══════════ CRD selectors
             │ ServiceMonitor   │ Dashboard JSON     │ AlertmanagerConfig
             │ (release=        │ (inputs:           │ → Secret webhook
             │  kube-prom-stack)│  Prometheus)       │ → Slack
             │                 │                     │
   ┌─────────┼─────────────────┴─────────────────────┴─────────────┐
   │         │              namespace: insighthub-dev               │
   │   ┌─────┴──────┐                                               │
   │   │ Service api│  port http/8000  →  GET /metrics              │
   │   │            │  (prometheus-client trong metrics.py)         │
   │   └────────────┘                                               │
   │   web   ingestion-worker   postgres   redis                    │
   └────────────────────────────────────────────────────────────────┘
```

**Các thành phần cấu hình (đã có sẵn trong repo `observability/`):**

| File | Loại | Vai trò |
|---|---|---|
| `servicemonitor.yaml` | ServiceMonitor CRD | Bảo Prometheus scrape `api` (và `worker` nếu có) |
| `prometheus-rules.yaml` | PrometheusRule CRD | 8 recording rule (baseline + 3σ) + 5 alert rule |
| `anomaly-rules.yaml` | File rules thuần | Bản standalone để validate bằng `promtool` |
| `alertmanager-config.yaml` | AlertmanagerConfig CRD + Secret | Route alert → Slack |
| `grafana-dashboards/insighthub-dashboard.json` | Dashboard JSON | ≥9 panel RED + USE |

> **Quy ước sống còn:** mọi CRD ở trên đều mang label `release: kube-prom-stack`. Prometheus Operator chỉ "nhận" các CRD khớp `serviceMonitorSelector`/`ruleSelector` = `release: kube-prom-stack`. **Thiếu label này = Prometheus bỏ qua, target trống.**

---

## Bước 0 — Chuẩn bị & kiểm tra điều kiện

```bash
# Đứng ở thư mục gốc dự án insighthub/
cd insighthub

# 0.1 — Công cụ
kubectl version --client          # cần kubectl
helm version                      # cần Helm 3.x
kubectl get nodes                 # cluster phải Ready

# 0.2 — InsightHub đang chạy
kubectl get pods -n insighthub-dev
```

✅ **Kết quả mong đợi:** 5 pod `Running` (`api`, `ingestion-worker`, `web`, `postgres`, `redis`).
Nếu chưa có namespace/pod → deploy InsightHub (Day 3) trước rồi quay lại.

---

## Bước 1 — Cài kube-prometheus-stack

`kube-prometheus-stack` là Helm chart "tất cả trong một" gồm **Prometheus + Grafana + Alertmanager + Prometheus Operator + node-exporter + kube-state-metrics**. Đây là cách chuẩn để dựng cả stack trên K8s.

```bash
# 1.1 — Thêm Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# 1.2 — Cài (pin version để tái lập được kết quả)
helm upgrade --install kube-prom-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --version 86.1.0 \
  --set prometheus.prometheusSpec.retention=15d \
  --set prometheus.prometheusSpec.resources.requests.memory=256Mi \
  --set prometheus.prometheusSpec.resources.limits.memory=512Mi \
  --set alertmanager.enabled=true \
  --set grafana.enabled=true \
  --set grafana.adminPassword=insighthub-dev \
  --wait --timeout=600s
```

**Giải thích các tham số:**
- `--version 86.1.0` — ghim phiên bản chart (đổi sang bản mới nhất nếu cần; ghim giúp mọi học viên có kết quả giống nhau).
- `retention=15d` — Prometheus giữ metric 15 ngày (đủ cho lab, tiết kiệm đĩa).
- `grafana.adminPassword=insighthub-dev` — mật khẩu admin Grafana (chỉ dùng cho lab; production phải dùng Secret).

```bash
# 1.3 — Verify
kubectl get pods -n monitoring
```

✅ **Kết quả mong đợi:** các pod `Running`:
```
kube-prom-stack-prometheus-operator-xxx     Running
prometheus-kube-prom-stack-prometheus-0     Running   (2/2)
alertmanager-kube-prom-stack-alertmanager-0 Running   (2/2)
kube-prom-stack-grafana-xxx                 Running   (3/3)
kube-prom-stack-kube-state-metrics-xxx      Running
kube-prom-stack-prometheus-node-exporter-xxx Running  (mỗi node 1)
```

> ⏱️ Lần đầu kéo image có thể mất vài phút. Nếu `--wait` timeout, chạy lại lệnh `helm upgrade --install` (idempotent).

---

## Bước 2 — Xác minh API có export /metrics

Trước khi cấu hình scrape, hãy chắc API thực sự phơi bày metric.

```bash
# 2.1 — Port-forward Service api
kubectl port-forward svc/api 8000:8000 -n insighthub-dev &

# 2.2 — Gọi /metrics, lọc metric của InsightHub
curl -s http://localhost:8000/metrics | grep insighthub_
```

✅ **Kết quả mong đợi:** thấy các dòng như:
```
# HELP insighthub_http_requests_total Tổng số HTTP request
insighthub_http_requests_total{method="POST",endpoint="/chat",status="200"} 12.0
insighthub_ingestion_queue_depth 0.0
insighthub_llm_call_latency_seconds_bucket{le="2.5"} 8.0
...
```

> Nếu trống: gọi vài request lên app (upload tài liệu, chat) để sinh metric, rồi thử lại. Counter/histogram chỉ xuất hiện sau khi có lưu lượng.

```bash
# 2.3 — Dừng port-forward khi xong
kill %1 2>/dev/null
```

> ℹ️ **Lưu ý về worker:** Hiện tại `metrics.py` chỉ instrument **API**. `ingestion-worker` **chưa chắc có** endpoint `/metrics`. ServiceMonitor cho worker ở Bước 3 vì vậy là **tùy chọn** — nếu worker chưa expose metric, target worker sẽ ở trạng thái down và bạn có thể bỏ qua nó cho tới khi worker được instrument.

---

## Bước 3 — ServiceMonitor: cho Prometheus scrape InsightHub

**ServiceMonitor** là Custom Resource (CRD) của Prometheus Operator. Thay vì sửa file config Prometheus thủ công, bạn khai báo một ServiceMonitor và Operator tự sinh cấu hình scrape.

File [`observability/servicemonitor.yaml`](../../observability/servicemonitor.yaml) (đã có sẵn) khai báo:
- Scrape Service có label `app.kubernetes.io/name: api`, port tên `http`, path `/metrics`, mỗi `30s`.
- Mang label `release: kube-prom-stack` để Operator nhận.

```bash
# 3.1 — Apply
kubectl apply -f observability/servicemonitor.yaml

# 3.2 — Verify CRD tồn tại
kubectl get servicemonitor -n insighthub-dev
```

✅ **Kết quả mong đợi:**
```
NAME                AGE
insighthub-api      10s
insighthub-worker   10s
```

```bash
# 3.3 — Sau 30-60s, kiểm tra Prometheus đã scrape được target chưa
kubectl port-forward svc/kube-prom-stack-prometheus -n monitoring 9090:9090 &

curl -s "http://localhost:9090/api/v1/targets" | \
  jq '.data.activeTargets[] | select(.labels.job | test("insighthub")) | {job:.labels.job, health:.health}'
```

✅ **Kết quả mong đợi:** `insighthub-api` có `"health":"up"`.
(Target `insighthub-worker` có thể `down` nếu worker chưa expose `/metrics` — xem lưu ý Bước 2.)

```bash
# 3.4 — Truy vấn thử 1 metric đã được lưu vào Prometheus
curl -s "http://localhost:9090/api/v1/query?query=insighthub_ingestion_queue_depth" | jq '.data.result'
```

✅ **Kết quả mong đợi:** mảng kết quả có giá trị (không rỗng).

> 🔑 **Vì sao bắt buộc label `release: kube-prom-stack`?**
> ```bash
> kubectl get prometheus -n monitoring \
>   -o jsonpath='{.items[0].spec.serviceMonitorSelector}' | jq
> # → {"matchLabels":{"release":"kube-prom-stack"}}
> ```
> Prometheus chỉ chọn ServiceMonitor khớp selector này. Thiếu label = không scrape = target trống.

---

## Bước 4 — PrometheusRule: recording + alert rules

**Recording rule** = tính sẵn biểu thức phức tạp thành metric mới (nhanh hơn, tái dùng). **Alert rule** = điều kiện bắn cảnh báo.

File [`observability/prometheus-rules.yaml`](../../observability/prometheus-rules.yaml) định nghĩa **anomaly band 3σ**:
```
baseline   = avg_over_time(current[30m])              # KHÁC giá trị hiện tại
upper_band = baseline + 3 × stddev_over_time(current[30m])
```
→ ~99.7% dữ liệu bình thường nằm trong band; vượt band = thực sự bất thường.
> ⚠️ Baseline phải là cửa sổ **dài (30m)**, không lấy chính `current` — nếu `upper_band = current + 3σ`
> thì `current > upper_band` rút gọn thành `0 > 3σ` ⇒ alert không bao giờ fire. Lab dùng thêm
> ngưỡng tuyệt đối (vd LLM avg5m > 5s) làm fallback khi baseline 30m chưa tích đủ.

```bash
# 4.1 — (Khuyến nghị) Validate cú pháp rules trước khi apply
promtool check rules observability/anomaly-rules.yaml
```
✅ **Kết quả mong đợi:** `SUCCESS: 13 rules found` (8 recording + 5 alert).
> Chưa có `promtool`? Cài qua gói `prometheus` (`brew install prometheus` / tải binary). Bước này tùy chọn nhưng nên làm.

```bash
# 4.2 — Apply PrometheusRule CRD
kubectl apply -f observability/prometheus-rules.yaml

# 4.3 — Verify
kubectl get prometheusrule -n insighthub-dev
# → insighthub-rules

# 4.4 — Kiểm tra Prometheus đã nạp rule (cần port-forward 9090 như Bước 3.3)
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].name' | grep insighthub
```
✅ **Kết quả mong đợi:** `"insighthub.recording"` và `"insighthub.alerts"`.

```bash
# 4.5 — Kiểm tra recording rule đã sinh giá trị (cần có lưu lượng + thời gian)
curl -s "http://localhost:9090/api/v1/query?query=job:insighthub_error_rate:rate5m" | jq '.data.result'
```

> ⏱️ **Quan trọng:** Recording rule `stddev30m` cần **≥30 phút baseline** mới có ý nghĩa. Trong lab chỉ chạy 5-10 phút → band có thể hẹp, dễ false-positive. Đây là hạn chế đã biết của phương pháp 3σ, không phải lỗi cấu hình.

---

## Bước 5 — Truy cập Grafana & cấu hình datasource

```bash
# 5.1 — Port-forward Grafana (Service lắng nghe port 80, map ra 3001 cho dễ nhớ)
kubectl port-forward svc/kube-prom-stack-grafana -n monitoring 3001:80 &

# 5.2 — Mở trình duyệt
#   http://localhost:3001
#   User: admin   |   Password: insighthub-dev
```

✅ **Datasource Prometheus đã có sẵn:** kube-prometheus-stack tự động tạo datasource trỏ tới Prometheus nội bộ. Kiểm tra: **Connections → Data sources → Prometheus** → bấm **Test** → "Data source is working".

> Nếu vì lý do nào đó datasource chưa có: **Add data source → Prometheus**, URL = `http://kube-prom-stack-prometheus.monitoring.svc:9090`, **Save & test**.

---

## Bước 6 — Import dashboard InsightHub

Dashboard [`observability/grafana-dashboards/insighthub-dashboard.json`](../../observability/grafana-dashboards/insighthub-dashboard.json) có ≥9 panel theo **RED method** (Rate, Errors, Duration) + USE.

> ⚠️ **Lưu ý quan trọng:** File JSON khai báo một input datasource tên `datasource` (khối `__inputs`). Khi import **bắt buộc phải ánh xạ input này tới datasource Prometheus**, nếu không panel sẽ hiện *"No data"* do biến `${datasource}` chưa được giải.

### Cách A — Import qua UI (khuyến nghị cho học viên)

1. Vào Grafana → **Dashboards → New → Import**.
2. **Upload JSON file** → chọn `observability/grafana-dashboards/insighthub-dashboard.json`.
3. Ở mục **datasource**, Grafana sẽ hỏi → **chọn `Prometheus`** từ dropdown.
4. Bấm **Import**.

✅ **Kết quả mong đợi:** mở dashboard **"InsightHub — AIOps Dashboard"** (uid `insighthub-aiops`), các panel hiển thị dữ liệu (không "No data" — với điều kiện app đã có lưu lượng).

### Cách B — Import qua API (tự động hóa)

Khi import bằng API, **phải kèm mảng `inputs`** để ánh xạ datasource, nếu không panel sẽ "No data":

```bash
DASHBOARD_JSON=$(cat observability/grafana-dashboards/insighthub-dashboard.json)

curl -s -X POST \
  -H "Content-Type: application/json" \
  -u admin:insighthub-dev \
  "http://localhost:3001/api/dashboards/import" \
  -d "{
    \"dashboard\": $DASHBOARD_JSON,
    \"overwrite\": true,
    \"inputs\": [
      {\"name\": \"datasource\", \"type\": \"datasource\", \"pluginId\": \"prometheus\", \"value\": \"Prometheus\"}
    ]
  }" | jq '{status, uid, slug}'
```

✅ **Kết quả mong đợi:** `"status": "success"` (hoặc HTTP 200) với `uid: "insighthub-aiops"`.
> `value: "Prometheus"` phải khớp **tên** datasource trong Grafana (xem Bước 5). Nếu tên khác, sửa lại cho khớp.

### Các panel chính & PromQL đằng sau

| Panel | PromQL | Ý nghĩa |
|---|---|---|
| Request Rate | `rate(insighthub_http_requests_total[2m])` | req/giây |
| Error Rate | `job:insighthub_error_rate:rate5m` | % 5xx |
| RAG p95 Latency | `job:insighthub_rag_latency_p95:5m` | độ trễ truy vấn p95 |
| LLM Latency + Band | `..._avg5m` cùng `..._upper_band` | spike vượt band |
| Queue Depth | `insighthub_ingestion_queue_depth` | backlog ingest |

---

## Bước 7 — Alertmanager → Slack

Khi alert rule (Bước 4) fire, **Alertmanager** nhóm và định tuyến cảnh báo tới kênh phù hợp. InsightHub route theo `severity`:
- `warning` → `#insighthub-alerts`
- `critical` → `#insighthub-oncall`

File [`observability/alertmanager-config.yaml`](../../observability/alertmanager-config.yaml) gồm một **AlertmanagerConfig CRD** + một **Secret** chứa webhook URL (cách chuẩn — không hardcode webhook trong CRD).

```bash
# 7.1 — Tạo Slack Incoming Webhook
#   https://api.slack.com/apps → Create App → Incoming Webhooks → bật → Add New Webhook
#   Tạo 2 channel trước: #insighthub-alerts và #insighthub-oncall

# 7.2 — Điền webhook vào Secret (thay placeholder trong file)
#   Mở observability/alertmanager-config.yaml, thay:
#     webhook-url: "<YOUR_SLACK_WEBHOOK_URL>"
#   bằng URL thật, vd https://hooks.slack.com/services/T000/B000/XXXX

# 7.3 — Apply (gồm cả AlertmanagerConfig CRD và Secret)
kubectl apply -f observability/alertmanager-config.yaml

# 7.4 — Verify
kubectl get alertmanagerconfig -n insighthub-dev
# → insighthub-alertmanager
kubectl get secret alertmanager-slack-webhook -n insighthub-dev
# → tồn tại
```

> 🔐 **Vì sao dùng Secret thay vì dán webhook vào CRD?** Webhook URL là bí mật (ai có nó đều gửi được message vào kênh). Để trong Secret giúp tách bí mật khỏi config, đúng nguyên tắc *"không hardcode secret"* của dự án.

```bash
# 7.5 — Test gửi alert giả qua Alertmanager
kubectl port-forward svc/kube-prom-stack-alertmanager -n monitoring 9093:9093 &

curl -s -XPOST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{"labels":{"alertname":"TestAlert","severity":"warning","incident":"smoke-test"},
        "annotations":{"summary":"Test alert từ Day 4 setup"}}]'
```

✅ **Kết quả mong đợi:** trong vài giây, message xuất hiện ở Slack `#insighthub-alerts` với tiêu đề `[FIRING:1] TestAlert`.

> Nếu Slack không nhận: test webhook trực tiếp `curl -XPOST <webhook> -d '{"text":"hi"}'`; xem log `kubectl logs -l app.kubernetes.io/name=alertmanager -n monitoring`.

---

## Bước 8 — Verify toàn bộ stack

```bash
bash scripts/verify-day-4.sh
```
✅ **Kết quả mong đợi:** `9/9 PASS`.

**Checklist thủ công:**
```text
[ ] kubectl get pods -n monitoring             → Prometheus/Grafana/Alertmanager Running
[ ] kubectl get servicemonitor -n insighthub-dev → insighthub-api tồn tại
[ ] curl prom:9090/api/v1/targets               → insighthub-api health=up
[ ] kubectl get prometheusrule -n insighthub-dev → insighthub-rules tồn tại
[ ] promtool check rules observability/anomaly-rules.yaml → SUCCESS: 13 rules
[ ] Grafana → dashboard "InsightHub — AIOps" có data, không "No data"
[ ] Test alert → tới Slack #insighthub-alerts
```

🎯 **Hoàn tất!** Bạn đã có observability stack đầy đủ. Tiếp theo → đọc [`DAY_04_README.md`](../../DAY_04_README.md) để thực hành **inject 3 incident** (LLM latency spike, queue backlog, error burst) và viết **AI RCA report**.

---

## Phụ lục — Troubleshooting

### Target trống / ServiceMonitor không scrape
```bash
# Label phải đúng
kubectl get servicemonitor insighthub-api -n insighthub-dev -o jsonpath='{.metadata.labels}' | jq
#   → phải có "release":"kube-prom-stack"

# Port name của Service api phải là "http"
kubectl get svc api -n insighthub-dev -o jsonpath='{.spec.ports[*].name}'
#   → http
```

### `up == 0` cho insighthub-api
```bash
kubectl get endpoints api -n insighthub-dev     # phải có IP:8000
kubectl exec deployment/api -n insighthub-dev -- curl -s localhost:8000/metrics | head -3
```

### Alert không fire dù vượt ngưỡng
```bash
# Recording rule đã có giá trị chưa? (band cần baseline đủ lâu)
curl -s "http://localhost:9090/api/v1/query?query=job:insighthub_llm_latency_upper_band" | jq '.data.result'
# Xem trạng thái alert
curl -s "http://localhost:9090/api/v1/alerts" | jq '.data.alerts[] | select(.labels.alertname | test("InsightHub"))'
```

### Grafana panel "No data"
1. Datasource OK? **Connections → Data sources → Prometheus → Test**.
2. Import có ánh xạ input `datasource` → `Prometheus` chưa? (Bước 6 — lỗi phổ biến nhất.)
3. App có lưu lượng chưa? Counter/histogram chỉ có giá trị sau khi có request.

### Slack không nhận alert
```bash
kubectl get alertmanagerconfig -n insighthub-dev
curl -s -X POST "<YOUR_SLACK_WEBHOOK_URL>" -H 'Content-type: application/json' -d '{"text":"test"}'
kubectl logs -l app.kubernetes.io/name=alertmanager -n monitoring | tail -20
```

### Dọn dẹp port-forward
```bash
# Liệt kê & kill các tiến trình port-forward đang chạy nền
jobs
kill %1 %2 %3 2>/dev/null
```

---

## Tham khảo

| Tài nguyên | Đường dẫn |
|---|---|
| Mentor guide Day 4 (incident + RCA + MLOps) | [`DAY_04_README.md`](../../DAY_04_README.md) |
| File cấu hình observability | [`observability/`](../../observability/) |
| Định nghĩa metric (instrumentation) | [`api/app/core/metrics.py`](../../api/app/core/metrics.py) |
| Prometheus docs | https://prometheus.io/docs/ |
| Grafana docs | https://grafana.com/docs/grafana/latest/ |
| kube-prometheus-stack | https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack |
| PromQL cheat sheet | https://promlabs.com/promql-cheat-sheet/ |
