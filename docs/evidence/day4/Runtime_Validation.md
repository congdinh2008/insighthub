# Day 04 runtime validation

## Environment

- Date: 2026-09-23, Asia/Ho_Chi_Minh.
- Source baseline: `main` commit `1dfa6b76ceca5e1e659545c535ad3c3266f495a2` plus the Day 04 branch changes under validation.
- Kubernetes: local Kind cluster `insighthub-local`, application namespace `insighthub-dev`, monitoring namespace `monitoring`.
- Application Helm revision: 4.
- kube-prometheus-stack: chart `89.2.0`, revision 4 during incidents; revision 6 after Grafana local render fix.
- InsightHub observability chart revision: 7 during incidents; revision 9 after the rule and MCP read-only ServiceAccount review.
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
| Dashboard | UID `insighthub-day4`, 9 query panels and 1 deployment annotation loaded by Grafana; 9/9 panels rendered data without "No data" in the 15:40-16:05 UTC incident range ([screenshot](grafana-day4-9-panels.png), [panel validation](dashboard-panel-validation.json)) |
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
| Reviewed generation price | Zenlayer dashboard captured 2026-09-23: input `$5.00/M token`, output `$30.00/M token`; [pricing evidence](zenlayer-gpt-5.6-sol-pricing.png) |
| Baseline continuity | 4,505 seconds; 70/70 chat requests returned HTTP 200; 75 one-minute chat/token samples, 75 finite p95 samples and 76 queue samples |
| Baseline usage and cost | 10,640 input tokens and 8,599 output tokens; estimated generation cost `$0.31117`, within the `$5` budget; [structured evidence](baseline.json) |
| LLM latency incident | Pending, firing, Slack FIRING, recovery, resolved and Slack RESOLVED observed; p95 `19.470588235294116`, upper band `10.05`, volume `20` |
| Queue backlog incident | Pending, firing, Slack FIRING, worker recovery, resolved and Slack RESOLVED observed; queue depth `20`, upper band `3`, worker desired replicas `0` |
| Error burst incident | Pending, firing, Slack FIRING, recovery, resolved and Slack RESOLVED observed; error ratio `1`, upper band `0.015`, request volume `32.23198631126321` |
| Recovery Browser E2E | At `2026-09-23T16:25:00Z`, the UI returned the expected under-five-minute target, cited `day4-zenlayer-smoke.txt` and reported 3700 ms latency |
| Final provider usage and cost | 29,254 input tokens and 17,901 output tokens; estimated generation cost `$0.68330`, within the `$5` budget |
| Day 04 verifier | Re-run 2026-09-24: PASS in real mode, 3 incidents, 8 finite live samples, source digest matched; `scope=partial-runtime-contract`, `milestone_complete=false` ([report](verifier-day4.json)) |
| MCP investigation | 8 Prometheus range queries matched the RCA samples and Kubernetes MCP listed current pods read-only on 2026-09-24 ([calls](mcp-investigation.json)); this is post-incident evidence |

## Runtime defects found and corrected

1. PostgreSQL and Redis exporters were running but absent from Prometheus because their Service metadata lacked the component label selected by the ServiceMonitors. The labels were added and the targets became `up=1` after the next scrape.
2. Prometheus target label `endpoint=http` overwrote the API route label. `honorLabels: true` was added to API and worker ServiceMonitors so route-based RED queries retain `/chat` and other bounded route templates.
3. The existing Kind containers survived while the local kubeconfig context was missing. The Day 04 local lab tool now exports the context before deploy and status operations.
4. Prometheus Operator initially injected `namespace="monitoring"` into the Slack route, so a project-scoped Day 04 test alert could not match. `alertmanagerConfigMatcherStrategy.type: None` now preserves the explicit `project="insighthub"` matcher; the repeated test reached Slack.
5. The requested Zenlayer model `gpt-6-sol` was absent from the key's model catalog and returned HTTP 403. The trainer approved `gpt-5.6-sol`; direct compatibility and InsightHub E2E calls both succeeded.
6. The existing index used the fixture embedding identity and correctly rejected the real embedding model. The three RAG tables were backed up to `/tmp/insighthub-day4-rag-backup-20260923.sql` before reset; SHA-256 `477f407a08e9208abde9a318acc9215d26808f10dc442b46100a41fec6ad3e9b`.
7. The real-provider example still targeted the OpenAI upstream. It now targets the reviewed Zenlayer origin so future Day 04 real-mode deploys retain the validated route.
8. Empty five-minute histogram windows produced `NaN` p95 samples. The baseline mean and standard deviation now filter non-finite p95 values before calculating the anomaly band.
9. Before the first HTTP 5xx series existed, the error-ratio numerator produced no vector and could not record a zero baseline. The ratio now falls back to zero, and the one-hour continuity guard uses the continuously recorded request-volume series.
10. On 2026-09-24, Grafana 13.2.1-distroless attempted to auto-update its bundled Prometheus plugin on a read-only filesystem. The plugin was not registered and all panels rendered "No data" despite stored Prometheus samples. Disabled `plugins.preinstall_auto_update` in the reproducible local Helm values. Grafana also approached its prior 500m CPU/512Mi memory limits while rendering nine panels; local limits are now 1 CPU/1 GiB. The datasource health returned `OK` and all nine panels rendered before the screenshot was accepted.

## Incident evidence

- LLM latency: [FIRING](https://insighthubdo2603.slack.com/archives/C0C3DP9B4H5/p1790178236224429), [RESOLVED](https://insighthubdo2603.slack.com/archives/C0C3DP9B4H5/p1790178416099459), [RCA](incident-llm-latency.json).
- Queue backlog: [FIRING](https://insighthubdo2603.slack.com/archives/C0C3DP9B4H5/p1790178716316169), [RESOLVED](https://insighthubdo2603.slack.com/archives/C0C3DP9B4H5/p1790178836080329), [RCA](incident-queue-backlog.json).
- Error burst: [FIRING](https://insighthubdo2603.slack.com/archives/C0C3DP9B4H5/p1790179136306809), [RESOLVED](https://insighthubdo2603.slack.com/archives/C0C3DP9B4H5/p1790179256083209), [RCA](incident-error-burst.json).

## Review correction - 2026-09-24

The 2026-09-23 baseline and incident observations are historical. On 2026-09-24,
the Redis-down and NaN warmup rule edge cases were fixed; promtool, static tests,
live Prometheus citation checks and panel-data checks passed. Grafana was
restarted with its plugin and local resource fix, then a dashboard screenshot
was captured showing nine panels with data. The new verifier PASS covers only
its declared partial runtime contract. MCP calls made during this review query
retained history; they do not prove the coding host called MCP during the
original incident. The trainer requested a professional Day 04 prompt list
instead of a historical prompt log; see [Day 04 prompts](../../../ai-prompts/day4.md)
and [Review and self-check](../../day4/Review_and_Self_Check.md).

The trainer excluded the quiz. The `$0.68330` figure is recorded generation
estimate, not total API billing; embeddings and other charges are excluded.
