# [Day 4] Add InsightHub observability and evidence-based incident RCA

InsightHub had a deployed async pipeline but no complete operational view of API latency/errors, queue backlog or all five components. This change adds bounded application metrics, PostgreSQL/Redis exporters, ServiceMonitors, a nine-panel RED/USE dashboard, one-hour anomaly bands, three alert rules and Slack routing. It also adds recoverable lab scripts for LLM latency, queue backlog and error burst plus the evidence-first RCA workflow and MLOps overview artifacts.

Validation includes Helm render/lint, promtool rule checks/tests, 5/5 Day 04 tests, full local targets/rules, a 75-minute recorded baseline and Zenlayer real-provider browser E2E. The baseline completed 70/70 chats with continuous telemetry. LLM latency, queue backlog and error burst each reached pending and firing, delivered FIRING and RESOLVED messages to Slack, recovered and produced a distinct RCA with live Prometheus samples. The final provider usage was 29,254 input tokens and 17,901 output tokens, an estimated `$0.68330` against the `$5` budget. The real-mode verifier passed all three incidents and matched the source digest. The trainer excluded the official quiz from this implementation scope.

Review on 2026-09-24 fixed the Redis-down queue fallback and NaN latency warmup
guard. Both promtool suites and five Day 04 tests pass. The loaded Grafana
dashboard has finite data on all nine panels and its deployment annotation in
the incident window. A local Grafana screenshot now shows all nine panels with
rendered data and no "No data" state. This required disabling auto-update of
the bundled Prometheus plugin on the read-only Grafana image and increasing
Grafana's local resource limits. A read-only MCP client made eight historical Prometheus
queries matching the RCA samples and listed current Kubernetes pods. The live
verifier passes with the updated source digest but declares a partial runtime
contract, not milestone completion. Original incident-time host MCP provenance
remains unverified. At the trainer's request, `ai-prompts/day4.md` is a
professional seven-prompt implementation list covering the Day 04 workflow,
not a historical prompt log. The detailed RCA prompt remains in
`prompts/rca-template.md`. Generation cost excludes embedding and other
charges. No remote push is part of this change.
