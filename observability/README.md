# InsightHub Day 04 observability

Phạm vi này triển khai đúng mục 8 của specification:

- kube-prometheus-stack pin tại chart `89.2.0`, Prometheus retention 15 ngày và resource limits.
- Bốn ServiceMonitor cho API, worker, PostgreSQL exporter và Redis exporter. Web cùng năm component được quan sát bằng kube-state-metrics/kubelet.
- Dashboard đúng chín query panels: rate, error, duration, queue, tokens, LLM p95, estimated generation API cost, resources/health và deployment history.
- Recording/anomaly rules cho LLM latency, queue backlog và error ratio, dùng baseline 1 giờ offset 10 phút.
- AlertmanagerConfig tới Slack `#alerts`, chỉ bật khi Secret runtime tồn tại.
- Fault proxy và scripts tái lập ba incident; không có autonomous remediation.

Nguồn canonical:

- `chart/files/anomaly-rules.yaml`
- `tests/anomaly-rules.test.yaml`
- `chart/files/insighthub-dashboard.json`
- `kube-prometheus-stack-values.yaml`

Quy trình chạy, real provider, Slack secret, baseline và cleanup nằm trong [Runbook](../docs/day4/Runbook.md). Không commit API key, Slack webhook, kubeconfig, port-forward log hoặc raw provider response.
