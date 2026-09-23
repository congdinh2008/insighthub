# Day 04 review and self-check

## Current status

| Area | Status | Evidence required to close |
|---|---|---|
| Source and static contracts | complete | lint, Helm, promtool, mypy and tests passed |
| Local monitoring runtime | complete in fixture mode | all pods ready, 4/4 targets UP, 20 rules healthy, 9-panel dashboard imported |
| Baseline >=1 hour | pending | continuous recorded samples and guards |
| Slack delivery | pending external runtime input | test and incident messages in `#alerts` |
| Three incidents and RCA | pending runtime | three distinct JSON reports with live samples |
| MLOps notes | complete | `mlops-overview-notes.md` |
| Quiz | practice 5/5; official pending | official form/result if supplied |

Runtime validation details are recorded in `docs/evidence/day4/Runtime_Validation.md`. Fixture mode does not emit provider-reported token usage and cannot close the token/cost, real-provider incident or Slack acceptance gates.

## AIOps self-check

1. Scrape interval is 30 seconds for API, worker and exporters. kube-state-metrics/kubelet cover the web and workload resources. The interval is sufficient for this lab but must be tuned against load/cardinality in production.
2. A 3-sigma band is not assumed to have a fixed false-positive rate unless distribution, independence and stationarity assumptions hold. One hour is a lab minimum.
3. Queue backlog is likely easiest to detect because it is a direct gauge with a clear impact floor. Latency quantiles and error ratios require enough events and correct denominators.
4. Each final RCA must cite exact Prometheus metric, labels, timestamp and value. Confidence is evidence-dependent and is not forced above 0.7.
5. Correlation is applied across queue depth, worker replicas/job completion and document readiness in incident 2; the controlled worker scale change establishes stronger causal evidence than time correlation alone.

## MLOps self-check

Answers for artifact differences, lifecycle, ownership, drift, retraining and rollback are in `mlops-overview-notes.md`. No notes are represented as an implemented MLOps system.
