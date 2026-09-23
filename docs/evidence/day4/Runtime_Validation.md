# Day 04 fixture runtime validation

## Environment

- Date: 2026-09-23, Asia/Ho_Chi_Minh.
- Source baseline: `main` commit `1dfa6b76ceca5e1e659545c535ad3c3266f495a2` plus the Day 04 branch changes under validation.
- Kubernetes: local Kind cluster `insighthub-local`, application namespace `insighthub-dev`, monitoring namespace `monitoring`.
- Application Helm revision: 3.
- kube-prometheus-stack: chart `89.2.0`, revision 2.
- InsightHub observability chart revision: 2.
- Runtime mode: fixture.

## Observed results

| Check | Result |
|---|---|
| Application workloads | API, web, ingestion worker, PostgreSQL and Redis ready |
| Exporters | PostgreSQL and Redis sidecars ready |
| Monitoring workloads | Prometheus, Alertmanager, Grafana, Operator, kube-state-metrics and node exporters ready |
| Required scrape targets | API, worker, PostgreSQL and Redis all returned `up=1` |
| Full local target health | 22 active targets, 22 UP, 0 DOWN after disabling unsupported Kind control-plane scrapes |
| Prometheus rules | 3 groups, 20 rules, all runtime rule health values `ok` |
| Anomaly alerts | exactly 3: LLM latency, queue backlog and error burst |
| Dashboard | UID `insighthub-day4`, 9 query panels and 1 deployment annotation loaded by Grafana |
| API smoke | `/healthz`, `/readyz` and fixture `/chat` succeeded |
| Browser smoke | document list rendered and the fixture RAG question returned an answer, source and latency |
| RED route labels | `/chat`, `/healthz`, `/readyz` and `/metrics` retained after enabling `honorLabels` |
| Storage and retention | Prometheus `15d` retention and `8Gi` persistent volume request |
| Day 04 Kubernetes MCP identity | six-hour token generated; pod list allowed and Secret read denied |

## Runtime defects found and corrected

1. PostgreSQL and Redis exporters were running but absent from Prometheus because their Service metadata lacked the component label selected by the ServiceMonitors. The labels were added and the targets became `up=1` after the next scrape.
2. Prometheus target label `endpoint=http` overwrote the API route label. `honorLabels: true` was added to API and worker ServiceMonitors so route-based RED queries retain `/chat` and other bounded route templates.
3. The existing Kind containers survived while the local kubeconfig context was missing. The Day 04 local lab tool now exports the context before deploy and status operations.

## Gates intentionally left pending

- No OpenAI or Gemini runtime credential is present.
- No Slack webhook Secret is present.
- Fixture generation reports token usage as unavailable, so token and cost acceptance cannot be claimed.
- The required baseline of at least one hour has not been collected.
- No incident was injected, no Slack notification was sent and no RCA JSON was created.
- The official quiz result is not available.

These gates require real external input and elapsed runtime. No synthetic token, Slack, incident or RCA evidence was created.
