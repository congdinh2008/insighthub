# DAY 04 — AIOps + MLOps Overview
## Hướng dẫn Mentor: Prometheus, Grafana, Anomaly Detection & AI RCA

> **Đối tượng:** Trainer / Mentor  
> **Thời lượng:** 2.5 giờ (150 phút)  
> **Branch học viên:** `day4-aiops`  
> **Pre-requisite:** kube-prometheus-stack installed trên cluster, InsightHub 5 pods Running

---

## Mục lục

1. [Tổng quan & Mục tiêu](#1-tổng-quan--mục-tiêu)
2. [Chuẩn bị trước buổi](#2-chuẩn-bị-trước-buổi)
3. [Cấu trúc buổi học](#3-cấu-trúc-buổi-học)
4. [Segment 1 — Recap & Hook](#4-segment-1--recap--hook)
5. [Segment 2 — Observability Stack Setup](#5-segment-2--observability-stack-setup)
6. [Segment 3 — Anomaly Detection Rules](#6-segment-3--anomaly-detection-rules)
7. [Segment 4 — Inject Incidents + AI RCA](#7-segment-4--inject-incidents--ai-rca)
8. [Segment 5 — MLOps Overview (25')](#8-segment-5--mlops-overview-25)
9. [Artifact Checklist](#9-artifact-checklist)
10. [Troubleshooting Guide](#10-troubleshooting-guide)

---

## 1. Tổng quan & Mục tiêu

### Bức tranh lớn

Day 3: InsightHub LIVE. User báo "đôi khi chậm" → không biết khi nào, ở đâu, tại sao.  
Day 4: **"I can see what's broken before users complain."**

AI RCA pattern: thay vì engineer mở 5 tab Grafana + mất 25 phút → AI agent query Prometheus MCP + K8s MCP + trả RCA report trong 2 phút.

### Mục tiêu học viên

| # | Mục tiêu | Artifact |
|---|---|---|
| 1 | ServiceMonitor + Prometheus scraping | `observability/servicemonitor.yaml` |
| 2 | Recording rules (anomaly bands 3σ) | `observability/anomaly-rules.yaml` |
| 3 | Grafana dashboard ≥ 9 panels RED+USE | `observability/grafana-dashboards/*.json` |
| 4 | Alertmanager → Slack | Test alert in Slack |
| 5 | 3 incident injection + AI RCA | `rca-reports/incident-*.json` |
| 6 | MLOps overview (4 blocks) | `mlops-overview-notes.md` |

---

## 2. Chuẩn bị trước buổi

### 2.1. Install kube-prometheus-stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade --install kube-prom-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set prometheus.prometheusSpec.retention=15d \
  --set prometheus.prometheusSpec.resources.requests.memory=256Mi \
  --set prometheus.prometheusSpec.resources.limits.memory=512Mi \
  --set alertmanager.enabled=true \
  --set grafana.enabled=true \
  --set grafana.adminPassword=insighthub-dev \
  --wait --timeout=300s

kubectl get pods -n monitoring
```

### 2.2. Kiểm tra InsightHub pods

```bash
kubectl get pods -n insighthub-dev
# Cần: 5/5 Running (api, ingestion-worker, web, postgres, redis)

# Kiểm tra /metrics endpoint
kubectl port-forward svc/api 8000:8000 -n insighthub-dev &
curl http://localhost:8000/metrics | grep insighthub_
```

### 2.3. Apply ServiceMonitor

```bash
kubectl apply -f observability/servicemonitor.yaml

# Verify
kubectl get servicemonitor -n insighthub-dev
# → insighthub-api  và insighthub-worker
```

### 2.4. Apply Prometheus Rules

```bash
kubectl apply -f observability/prometheus-rules.yaml

# Verify
kubectl get prometheusrule -n insighthub-dev
# → insighthub-rules

# Kiểm tra rules được load
kubectl port-forward svc/kube-prom-stack-prometheus -n monitoring 9090:9090 &
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].name' | grep insighthub
```

### 2.5. Cấu hình Alertmanager → Slack

```bash
# 1. Lấy Slack webhook URL từ https://api.slack.com/apps → Incoming Webhooks
# 2. Tạo Slack channels: #insighthub-alerts và #insighthub-oncall

# 3. Sửa webhook URL trong alertmanager-config.yaml
sed -i 's|<YOUR_SLACK_WEBHOOK_URL>|https://hooks.slack.com/services/XXX/YYY/ZZZ|' \
  observability/alertmanager-config.yaml

kubectl apply -f observability/alertmanager-config.yaml

# 4. Test alert
kubectl port-forward svc/kube-prom-stack-alertmanager -n monitoring 9093:9093 &
curl -XPOST http://localhost:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{"labels":{"alertname":"TestAlert","severity":"warning"},"annotations":{"summary":"Test từ Day 4"}}]'
```

### 2.6. Import Grafana Dashboard

```bash
kubectl port-forward svc/kube-prom-stack-grafana -n monitoring 3001:80 &
# Mở http://localhost:3001 — admin/insighthub-dev

# Import qua API
DASHBOARD_JSON=$(cat observability/grafana-dashboards/insighthub-dashboard.json)
curl -s -X POST \
  -H "Content-Type: application/json" \
  -u admin:insighthub-dev \
  "http://localhost:3001/api/dashboards/import" \
  -d "{\"dashboard\": $DASHBOARD_JSON, \"overwrite\": true, \"folderId\": 0}" | jq '.status'
```

---

## 3. Cấu trúc buổi học

| Thời gian | Segment | Nội dung |
|---|---|---|
| 0:00-0:10 | Recap & Hook | Từ "user complain" → "anomaly fire trước user" |
| 0:10-0:35 | Setup | ServiceMonitor + rules + Grafana import |
| 0:35-1:10 | Anomaly Rules | PromQL recording rules, 3σ concept, promtool |
| 1:10-1:45 | Incidents | Inject 3 incidents + AI RCA workflow |
| 1:45-2:10 | MLOps | 4-block overview, ownership boundary |
| 2:10-2:20 | Verify + Q&A | verify-day-4.sh, rubric review |

---

## 4. Segment 1 — Recap & Hook

Hook question: "Day 3 bạn deploy InsightHub lên K8s. Ngay lúc đó có 1 user upload 20 tài liệu. 15 phút sau họ báo 'tại sao tài liệu chưa sẵn sàng?' — bạn có bao nhiêu phút để tìm ra vấn đề?"

Demonstrate MTTR gap:
- **Manual**: mở Grafana (3min) → tìm query (5min) → correlate K8s events (10min) → diagnose (7min) = **~25min MTTR**
- **AI RCA với MCP**: query Prometheus MCP + K8s MCP (30s) → AI hypothesis (1min) → fix (5min) = **~7min MTTR**

---

## 5. Segment 2 — Observability Stack Setup

### 5.1. Tại sao ServiceMonitor cần label `release: kube-prom-stack`

Prometheus Operator tìm ServiceMonitor theo `serviceMonitorSelector`:
```bash
kubectl get prometheus -n monitoring -o jsonpath='{.items[0].spec.serviceMonitorSelector}' | jq
# → {"matchLabels":{"release":"kube-prom-stack"}}
```
Nếu thiếu label này → Prometheus không scrape → target UP = 0.

### 5.2. Verify scraping

```bash
# Sau 30-60s, targets phải UP
curl -s "http://localhost:9090/api/v1/targets" | \
  jq '.data.activeTargets[] | select(.labels.job | contains("insighthub")) | {job:.labels.job, health:.health}'

# Kiểm tra metric có data
curl -s "http://localhost:9090/api/v1/query?query=insighthub_ingestion_queue_depth" | jq '.data.result'
```

### 5.3. Grafana dashboard RED method

9 panel key:
- **Rate**: `rate(insighthub_http_requests_total[2m])` — requests/sec
- **Errors**: `job:insighthub_error_rate:rate5m` — % 5xx
- **Duration**: `job:insighthub_rag_latency_p95:5m` — p95 latency

---

## 6. Segment 3 — Anomaly Detection Rules

### 6.1. Giải thích 3σ method

```
upper_band = avg(metric[5m]) + 3 * stddev(metric[30m])
```

- `avg[5m]`: smoothed current value (loại bỏ outlier tức thời)
- `stddev[30m]`: biến động trong 30 phút gần nhất
- `3σ`: ~99.7% data trong baseline → fire khi thực sự bất thường

Nhược điểm: **cần baseline ≥ 30 phút** trước khi alert có ý nghĩa. Lab: 5-10 phút → có thể false positive.

### 6.2. Validate rules

```bash
promtool check rules observability/anomaly-rules.yaml
# → SUCCESS: 13 rules found (8 recording + 5 alert)
```

### 6.3. Test alert firing

```bash
# Simulate queue depth spike bằng cách modify gauge trực tiếp (lab only)
kubectl exec -it deployment/api -n insighthub-dev -- \
  python3 -c "from app.core.metrics import ingestion_queue_depth; ingestion_queue_depth.set(100)"
# → Alert InsightHubQueueDepthAnomaly fire trong ~2m
```

---

## 7. Segment 4 — Inject Incidents + AI RCA

### 7.1. Incident #1 — LLM Latency Spike

```bash
# Inject: thêm 8s delay vào LLM calls
bash scripts/chaos/inject-llm-latency.sh 8000 300

# Theo dõi: Grafana → "LLM Call Latency + Anomaly Band"
# Alert InsightHubLLMLatencyAnomaly fire trong ~2m

# AI RCA prompt
```

**AI RCA Prompt** (evidence-first):
```
Alert: InsightHubLLMLatencyAnomaly đang fire.

Protocol:
1. Query Prometheus: job:insighthub_llm_call_latency_seconds:avg5m [range: 30m]
2. Query Prometheus: job:insighthub_llm_latency_upper_band [range: 30m]  
3. Query K8s: kubectl top pods -n insighthub-dev
4. Query Prometheus: insighthub_llm_tokens_total rate [range: 30m]

Cite tất cả metric + timestamp. Output JSON: {top_hypotheses, root_cause, recommended_actions}
```

### 7.2. Incident #2 — Queue Backlog

```bash
bash scripts/chaos/inject-queue-backlog.sh 300

# Alert InsightHubQueueDepthAnomaly fire khi queue > upper_band + 1
```

### 7.3. Incident #3 — Error Burst

```bash
bash scripts/chaos/inject-error-burst.sh 180

# Alert InsightHubErrorRateAnomaly fire (critical) sau 1m
# Check Slack #insighthub-oncall
```

### 7.4. Lưu RCA reports

Sau mỗi incident, lưu AI output vào:
```bash
# Đã có sẵn: rca-reports/incident-{1,2,3}.json
# Học viên xem cấu trúc evidence + timestamp + hypotheses
```

---

## 8. Segment 5 — MLOps Overview (25')

Sử dụng `mlops-overview-notes.md` làm slide cơ sở. 4 blocks:

1. **Mindset** (5'): App artifact vs Model artifact — 4 chiều khác biệt
2. **Lifecycle** (7'): ML lifecycle map — DevOps own PRIMARY ở 4 stage
3. **Registry & Approval Gate** (7'): Tại sao cần human approval; pattern Staging → A/B → Production
4. **Drift & Rollback** (6'): Data drift vs Concept drift; ownership boundary table

**Key message cho học viên**: "DevOps KHÔNG BAO GIỜ tự retrain model. DevOps build infra cho ML team làm điều đó."

---

## 9. Artifact Checklist

```bash
bash scripts/verify-day-4.sh
# Kỳ vọng: 9/9 PASS
```

Manual checks:
```text
[ ] kubectl get servicemonitor -n insighthub-dev → exists
[ ] curl prom:9090/api/v1/targets → insighthub targets UP
[ ] Grafana dashboard URL → 12 panels, no "No data"
[ ] kubectl get prometheusrule -n insighthub-dev → exists
[ ] promtool check rules observability/anomaly-rules.yaml → SUCCESS: 13 rules
[ ] Test alert → reach Slack #insighthub-alerts
[ ] rca-reports/ có 3 JSON với evidence + timestamp
[ ] mlops-overview-notes.md có 4 block
```

---

## 10. Troubleshooting Guide

### ServiceMonitor không scrape (targets empty)

```bash
# 1. Kiểm tra label
kubectl get servicemonitor insighthub-api -n insighthub-dev -o jsonpath='{.metadata.labels}' | jq
# Phải có: "release": "kube-prom-stack"

# 2. Kiểm tra Prometheus selector
kubectl get prometheus kube-prom-stack-prometheus -n monitoring \
  -o jsonpath='{.spec.serviceMonitorSelector}' | jq
# Phải match label trên

# 3. Kiểm tra port name
kubectl get svc api -n insighthub-dev -o jsonpath='{.spec.ports[*].name}'
# Phải có port tên "http" (ServiceMonitor dùng port: http)
```

### Alert không fire dù metric vượt threshold

```bash
# 1. Kiểm tra recording rule đã compute
curl -s "http://localhost:9090/api/v1/query?query=job:insighthub_llm_latency_upper_band" | jq
# Nếu empty → recording rule chưa có data (cần thêm giây để scrape đủ)

# 2. Kiểm tra alert state
curl -s "http://localhost:9090/api/v1/alerts" | jq '.data.alerts[] | select(.labels.alertname | contains("InsightHub"))'
```

### Slack không nhận alert

```bash
# 1. Kiểm tra AlertmanagerConfig
kubectl get alertmanagerconfig -n insighthub-dev

# 2. Test webhook trực tiếp
curl -s -X POST "https://hooks.slack.com/services/YOUR/WEBHOOK/URL" \
  -H "Content-type: application/json" \
  -d '{"text":"Test từ Alertmanager"}'

# 3. Check Alertmanager logs
kubectl logs -l app.kubernetes.io/name=alertmanager -n monitoring | tail -20
```

### `up == 0` cho insighthub-api target

```bash
# Kiểm tra service endpoint
kubectl get endpoints api -n insighthub-dev

# Kiểm tra API expose /metrics
kubectl exec deployment/api -n insighthub-dev -- curl -s localhost:8000/metrics | head -5
```
