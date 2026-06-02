# observability/ — Prometheus, Grafana & Anomaly Detection (Day 4)

Cấu hình giám sát của InsightHub: Prometheus scrape `/metrics`, recording/alert rules theo phương pháp anomaly band 3σ, dashboard Grafana, và route alert tới Slack.

## 📖 Bắt đầu từ đâu?

➡️ **[docs/lab-guides/Day4-Prometheus-Grafana-Setup.md](../docs/lab-guides/Day4-Prometheus-Grafana-Setup.md)** — hướng dẫn cài đặt & cấu hình từng bước (đứng một mình, có giải thích khái niệm + "kết quả mong đợi").

➡️ **[../DAY_04_README.md](../DAY_04_README.md)** — kịch bản buổi học của mentor: inject incident + AI RCA + MLOps overview.

## 📂 Các file trong thư mục này

| File | Loại | Vai trò |
|---|---|---|
| `servicemonitor.yaml` | ServiceMonitor CRD | Bảo Prometheus scrape Service `api` (port `http` → `/metrics`, mỗi 30s). Worker là tùy chọn (chỉ scrape nếu worker expose `/metrics`). |
| `prometheus-rules.yaml` | PrometheusRule CRD | 8 recording rule (baseline + upper_band 3σ) + 5 alert rule. Apply lên cluster. |
| `anomaly-rules.yaml` | Rules file thuần | Bản standalone của các rule trên — dùng `promtool check rules` để validate cú pháp. |
| `alertmanager-config.yaml` | AlertmanagerConfig CRD + Secret | Route alert theo `severity` → Slack (`#insighthub-alerts` cho warning, `#insighthub-oncall` cho critical). Webhook lưu trong Secret. |
| `grafana-dashboards/insighthub-dashboard.json` | Grafana dashboard | 14 panel: RED + USE + anomaly band overlay + FinOps cost (USD/h) + Active Anomalies (đếm `ALERTS` firing); deploy events qua annotations overlay. Mọi stat bọc `or vector(0)` để tránh "No data". |

## ⚡ Quick apply

```bash
# Pre-req: kube-prometheus-stack đã cài (release name: kube-prom-stack), InsightHub 5 pods Running
kubectl apply -f observability/servicemonitor.yaml
kubectl apply -f observability/prometheus-rules.yaml
# Điền webhook Slack vào alertmanager-config.yaml trước khi apply:
kubectl apply -f observability/alertmanager-config.yaml
# Dashboard: import qua Grafana UI (nhớ ánh xạ datasource → Prometheus)
```

> 🔑 **Quy ước sống còn:** mọi CRD đều mang label `release: kube-prom-stack` để Prometheus Operator nhận diện. Thiếu label = bị bỏ qua.

Chi tiết verify từng bước + troubleshooting: xem [lab guide](../docs/lab-guides/Day4-Prometheus-Grafana-Setup.md).
