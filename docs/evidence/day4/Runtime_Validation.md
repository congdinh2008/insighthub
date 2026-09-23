# Day 04 runtime validation

## Environment

- Date: 2026-09-23, Asia/Ho_Chi_Minh.
- Source baseline: `main` commit `1dfa6b76ceca5e1e659545c535ad3c3266f495a2` plus the Day 04 branch changes under validation.
- Kubernetes: local Kind cluster `insighthub-local`, application namespace `insighthub-dev`, monitoring namespace `monitoring`.
- Application Helm revision: 4.
- kube-prometheus-stack: chart `89.2.0`, revision 4.
- InsightHub observability chart revision: 5.
- Runtime mode: fixture topology validation followed by a Zenlayer real-provider smoke run.

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
| API smoke | `/healthz`, `/readyz`, real-provider upload, ingestion, retrieval and `/chat` succeeded |
| Browser smoke | `day4-zenlayer-smoke.txt` rendered as `ready`; the UI returned `Aurora Lantern 274`, the recovery target, citation and latency |
| RED route labels | `/chat`, `/healthz`, `/readyz` and `/metrics` retained after enabling `honorLabels` |
| Storage and retention | Prometheus `15d` retention and `8Gi` persistent volume request |
| Day 04 Kubernetes MCP identity | six-hour token generated; pod list allowed and Secret read denied |
| Slack delivery | `FIRING` test alert delivered to `#alerts` at 16:36:09 ICT through `insighthub-do-2603` ([message](https://insighthubdo2603.slack.com/archives/C0C3DP9B4H5/p1790156169313959)) |
| Slack secret handling | Incoming webhook stored only in Kubernetes Secret `monitoring/insighthub-alertmanager-slack`, key `api-url`; no webhook value stored in Git or evidence |
| Real provider contract | Zenlayer `https://gateway.theturbo.ai`; chat `gpt-5.6-sol`; embedding `text-embedding-3-large`, 1024 dimensions |
| Real RAG response | mode `real`, provider `openai` compatibility, one source, citation present, 3160 ms API smoke latency |
| Provider usage | API and browser smoke totaled 319 generation input tokens, 80 generation output tokens, 48 document embedding tokens and 29 query embedding tokens |
| Prometheus telemetry | generation and embedding token series matched provider usage; LLM and RAG latency counters each recorded two calls |

## Runtime defects found and corrected

1. PostgreSQL and Redis exporters were running but absent from Prometheus because their Service metadata lacked the component label selected by the ServiceMonitors. The labels were added and the targets became `up=1` after the next scrape.
2. Prometheus target label `endpoint=http` overwrote the API route label. `honorLabels: true` was added to API and worker ServiceMonitors so route-based RED queries retain `/chat` and other bounded route templates.
3. The existing Kind containers survived while the local kubeconfig context was missing. The Day 04 local lab tool now exports the context before deploy and status operations.
4. Prometheus Operator initially injected `namespace="monitoring"` into the Slack route, so a project-scoped Day 04 test alert could not match. `alertmanagerConfigMatcherStrategy.type: None` now preserves the explicit `project="insighthub"` matcher; the repeated test reached Slack.
5. The requested Zenlayer model `gpt-6-sol` was absent from the key's model catalog and returned HTTP 403. The trainer approved `gpt-5.6-sol`; direct compatibility and InsightHub E2E calls both succeeded.
6. The existing index used the fixture embedding identity and correctly rejected the real embedding model. The three RAG tables were backed up to `/tmp/insighthub-day4-rag-backup-20260923.sql` before reset; SHA-256 `477f407a08e9208abde9a318acc9215d26808f10dc442b46100a41fec6ad3e9b`.
7. The real-provider example still targeted the OpenAI upstream. It now targets the reviewed Zenlayer origin so future Day 04 real-mode deploys retain the validated route.

## Gates intentionally left pending

- Zenlayer returned provider usage, but its model metadata exposed no pricing. Cost acceptance remains pending until reviewed input/output rates and their source are recorded.
- The required baseline of at least one hour has not been collected.
- No incident was injected and no RCA JSON was created. Slack transport is verified by the test alert, but incident-specific delivery remains pending.
- The trainer excluded the official quiz from this implementation scope. The repository practice quiz remains reference material only.

These remaining gates require reviewed Zenlayer prices, controlled incident runs and elapsed runtime. No synthetic token, incident or RCA evidence was created.
