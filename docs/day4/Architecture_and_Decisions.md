# Day 04 - Architecture and decisions

## Scope

Day 04 extends the Day 03 local Kubernetes deployment with telemetry, anomaly detection, Slack notification and evidence-first RCA. It does not add application features, ChatOps, automatic remediation, an ML platform or production AWS monitoring.

## Signal ownership

| Component | Source | Meaning |
|---|---|---|
| web | kube-state-metrics and kubelet/cAdvisor | replicas, readiness, restart, CPU and memory |
| api | `/metrics` and Kubernetes | RED, RAG/LLM duration, usage, document status and resources |
| ingestion-worker | `:8081/metrics` and Kubernetes | job outcomes/duration, readiness and resources |
| PostgreSQL | postgres-exporter | availability and connections/activity |
| Redis | redis-exporter | availability, memory and ARQ sorted-set size |

The ARQ queue is a Redis sorted set. `redis_key_size{key="insighthub:ingestion"}` is therefore used instead of `LLEN`. The recorded `ih:queue_depth` is named outstanding entries because ARQ may retain queued, deferred or in-progress entries in that set. When the key is absent, zero is emitted only while `redis_up` is present; a missing scrape is not converted to a healthy zero.

## Anomaly semantics

- Recording interval: 1 minute.
- Baseline: 1 hour, offset 10 minutes.
- Minimum recorded history: 70 minutes; runtime plan uses 75 minutes.
- Alert hold: 2 minutes.
- Latency impact floor: 1 second and at least 20 calls per 5 minutes.
- Queue impact floor: 10 outstanding entries.
- Error impact floor: 5 percent and at least 20 requests per 5 minutes.
- Sigma floors prevent a zero-variance baseline from producing an unusably narrow band.

The rules are statistical detectors for this bounded lab. They do not establish a production SLO, causal root cause or seven-day seasonal baseline.

## Fault boundaries

- Latency and error injection use a bounded provider proxy in normal, latency or error mode. The proxy can delay at most 10 seconds and caps request/response bodies at 2 MiB.
- Queue injection scales only `insighthub-ingestion-worker` in the selected lab namespace, stores its previous replica count and restores it.
- Scripts refuse a Kubernetes context other than the selected Day 04 context.
- Faults are sequential and require recovery before the next incident.
- AI and MCP access stays read-only. The operator executes every mutation and rollback.

## Cost panel

The panel uses provider-reported generation tokens multiplied by reviewed per-million-token configuration. It is an API estimate, not a cloud bill. It intentionally has no series while configured prices are zero. Acceptance requires recording the exact model, source URL, access date and nonzero reviewed prices before collecting real-mode evidence.
