# Day 04 fixture runtime validation

## Environment

- Date: 2026-09-23, Asia/Ho_Chi_Minh.
- Source baseline: `main` commit `1dfa6b76ceca5e1e659545c535ad3c3266f495a2` plus the Day 04 branch changes under validation.
- Kubernetes: local Kind cluster `insighthub-local`, application namespace `insighthub-dev`, monitoring namespace `monitoring`.
- Application Helm revision: 3.
- kube-prometheus-stack: chart `89.2.0`, revision 3.
- InsightHub observability chart revision: 3.
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
| Slack delivery | `FIRING` test alert delivered to `#alerts` at 16:36:09 ICT through `insighthub-do-2603` ([message](https://insighthubdo2603.slack.com/archives/C0C3DP9B4H5/p1790156169313959)) |
| Slack secret handling | Incoming webhook stored only in Kubernetes Secret `monitoring/insighthub-alertmanager-slack`, key `api-url`; no webhook value stored in Git or evidence |

## Runtime defects found and corrected

1. PostgreSQL and Redis exporters were running but absent from Prometheus because their Service metadata lacked the component label selected by the ServiceMonitors. The labels were added and the targets became `up=1` after the next scrape.
2. Prometheus target label `endpoint=http` overwrote the API route label. `honorLabels: true` was added to API and worker ServiceMonitors so route-based RED queries retain `/chat` and other bounded route templates.
3. The existing Kind containers survived while the local kubeconfig context was missing. The Day 04 local lab tool now exports the context before deploy and status operations.
4. Prometheus Operator initially injected `namespace="monitoring"` into the Slack route, so a project-scoped Day 04 test alert could not match. `alertmanagerConfigMatcherStrategy.type: None` now preserves the explicit `project="insighthub"` matcher; the repeated test reached Slack.

## Gates intentionally left pending

- No OpenAI or Gemini runtime credential is present.
- Fixture generation reports token usage as unavailable, so token and cost acceptance cannot be claimed.
- The required baseline of at least one hour has not been collected.
- No incident was injected and no RCA JSON was created. Slack transport is verified by the test alert, but incident-specific delivery remains pending.
- The official quiz result is not available.

These remaining gates require real provider input, controlled incident runs or elapsed runtime. No synthetic token, incident or RCA evidence was created.
