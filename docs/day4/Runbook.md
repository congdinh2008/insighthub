# Day 04 runbook

## 1. Preconditions

- Work only on branch `day4-observability` derived from merged Day 03 `main`.
- Docker Desktop, kubectl, Helm and the Day 03 `kind` binary are available.
- The selected context must be `kind-insighthub-local` unless `DAY4_KUBE_CONTEXT` explicitly selects another isolated lab.
- For implementation acceptance: a real OpenAI-compatible generation/embedding provider with usage, exact model prices, Slack workspace/channel `#alerts` and incoming webhook are available. The trainer excluded the official quiz from this implementation scope.
- Never put provider keys or the Slack webhook in source, commands pasted into evidence or screenshots.

## 2. Static verification

```bash
make helm-day4
make rules-day4
python -m pytest tests/milestones/day4 -v -p no:cacheprovider
make lint typecheck test-verifiers
```

`promtool` must validate and test the same canonical file later mounted in the PrometheusRule.

## 3. Start the fixture lab

```bash
make day4-local-up
make day4-local-status
```

The installer builds the Day 04 application images, reuses or creates the isolated kind cluster, installs kube-prometheus-stack `89.2.0`, then installs the application and observability charts. It does not create Slack or provider credentials.

Open local endpoints in separate terminals:

```bash
kubectl --context kind-insighthub-local -n insighthub-dev \
  port-forward service/insighthub-web 13000:3000
kubectl --context kind-insighthub-local -n insighthub-dev \
  port-forward service/insighthub-api 18000:8000
kubectl --context kind-insighthub-local -n monitoring \
  port-forward service/kube-prom-stack-kube-prome-prometheus 19090:9090
kubectl --context kind-insighthub-local -n monitoring \
  port-forward service/kube-prom-stack-grafana 13001:80
kubectl --context kind-insighthub-local -n monitoring \
  port-forward service/kube-prom-stack-kube-prome-alertmanager 19093:9093
```

Fixture mode verifies topology and dashboard loading only. It cannot satisfy token/cost or real-provider incident evidence.

## 4. Configure real runtime without committing secrets

Create `/tmp/insighthub-day4-runtime.env`, set mode `0600`, and include the full Kubernetes Secret values:

```text
DATABASE_URL=postgresql://insighthub:insighthub@postgres:5432/insighthub
REDIS_URL=redis://redis:6379/0
OPENAI_API_KEY=<runtime value>
OPENAI_BASE_URL=http://insighthub-provider-fault-proxy:8080/v1
OPENAI_CHAT_MODEL=<exact chat model>
OPENAI_EMBEDDING_MODEL=<exact embedding model>
```

Create or update the Secret locally:

```bash
kubectl --context kind-insighthub-local -n insighthub-dev create secret generic \
  insighthub-runtime --from-env-file=/tmp/insighthub-day4-runtime.env \
  --dry-run=client -o yaml | \
kubectl --context kind-insighthub-local apply -f -
```

Copy `deploy/helm/insighthub/values-day4-real.example.yaml` to a local ignored path or pass reviewed non-secret values with Helm. Set the exact token prices and retain the source URL/date in evidence. Deploy again with:

```bash
DAY4_APP_VALUES=deploy/helm/insighthub/values-day4-real.example.yaml \
DAY4_OBSERVABILITY_VALUES=observability/values-day4-real.example.yaml \
python tools/observability/local_lab.py up
```

Before baseline, upload a fresh Day 04 document and verify it reaches `ready`, then make one successful `/chat` request. Confirm token and price metrics exist. Never change embedding model/endpoint/revision on an existing index. Use a fresh lab dataset if the identity differs.

## 5. Configure Slack

Create the webhook file outside the repository with mode `0600`, then create the Secret:

```bash
kubectl --context kind-insighthub-local -n monitoring create secret generic \
  insighthub-alertmanager-slack --from-file=api-url=/tmp/insighthub-slack-webhook \
  --dry-run=client -o yaml | \
kubectl --context kind-insighthub-local apply -f -
```

Redeploy the observability chart with `alerting.slack.enabled=true`. Send one test alert only after confirming the workspace and channel:

```bash
DAY4_ALERTMANAGER_URL=http://127.0.0.1:19093 \
  ./scripts/chaos/send-test-alert.sh
```

Record alert timestamp and the Slack permalink or redacted screenshot. The verifier does not check delivery.

## 6. Verify targets and rules before baseline

```bash
curl -fsS http://127.0.0.1:19090/api/v1/targets
curl -fsS http://127.0.0.1:19090/api/v1/rules
kubectl --context kind-insighthub-local -n monitoring get servicemonitor,prometheusrule
```

Expected application targets are API, worker, PostgreSQL exporter and Redis exporter. Web/application Kubernetes metrics come from kube-state-metrics and kubelet/cAdvisor. Confirm all required targets are UP, all rules loaded without errors and all nine dashboard panels return meaningful data.

## 7. Collect baseline

Start only after rules are stable:

```bash
DAY4_API_URL=http://127.0.0.1:18000 \
DAY4_BASELINE_SECONDS=4500 \
  ./scripts/chaos/run-baseline.sh
```

The 75-minute run covers the 1-hour window plus 10-minute offset and a five-minute margin. Check `count_over_time` guards, sample continuity, no unexplained alert and provider cost before injecting faults. Raw metrics collected before recording rules were loaded do not backfill recorded series.

## 8. Incident 1 - LLM latency

```bash
DAY4_API_URL=http://127.0.0.1:18000 \
  ./scripts/chaos/inject-llm-latency.sh start
./scripts/chaos/inject-llm-latency.sh stop
```

Capture start, pending, firing, Slack and resolved timestamps. The alert must fire within five minutes. Confirm chat succeeds after recovery.

## 9. Incident 2 - Queue backlog

```bash
DAY4_API_URL=http://127.0.0.1:18000 \
DAY4_DOCUMENTS=20 \
  ./scripts/chaos/inject-queue-backlog.sh start
./scripts/chaos/inject-queue-backlog.sh stop
```

Confirm queue rises above 10, the alert fires, the saved replica count is restored, queue drains and uploaded documents reach `ready`.

## 10. Incident 3 - Error burst

```bash
DAY4_API_URL=http://127.0.0.1:18000 \
  ./scripts/chaos/inject-error-burst.sh start
./scripts/chaos/inject-error-burst.sh stop
```

Confirm the provider proxy causes server responses, the error ratio alert fires, Slack receives it and a normal chat succeeds after recovery.

## 11. Evidence-first RCA

Use the [Vietnamese RCA prompt](../../prompts/rca-template.md) for each incident
and the [Day 04 prompt workflow](../../ai-prompts/day4.md). Save actual host MCP
tool-call references and verified host metadata; a prompt template is not a run log.

For each incident, query Prometheus through the Day 04 Prometheus MCP and inspect pods/events/logs through the read-only Kubernetes MCP. Separate observed, inferred and unknown. Store exact query, time range and returned samples. Each final JSON must contain:

- unique `incident_id`, `started_at`, `ended_at`;
- hypotheses and falsifying checks;
- `samples` with Prometheus metric name, labels, exact timestamp and finite value;
- environment, source commit, root-cause assessment, confidence basis, action and recovery evidence.

Every verifier sample must still exist in live Prometheus and match the timestamp/value exactly.

## 12. Final verification and cleanup

```bash
./scripts/verify-day-4.sh \
  --evidence-dir docs/evidence/day4 \
  --prometheus-url http://127.0.0.1:19090 \
  --json
```

Then perform Browser E2E for the nine panels, annotation, alert state, Slack evidence and final InsightHub upload/chat/citations. Save dashboard screenshots with the selected time range. Record missing runtime inputs as pending; quiz is excluded by the trainer. Read the [current review](Review_and_Self_Check.md) before claiming complete acceptance.

Always restore fault mode and worker replicas before ending. Stop port-forwards. After evidence is saved and reviewed, remove the isolated lab with `make day4-local-down`. Do not use Docker prune or delete unrelated volumes/clusters.
