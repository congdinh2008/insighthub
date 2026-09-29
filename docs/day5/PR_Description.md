# fix(day5): harden ChatOps evidence, approvals and HTTP intake

The Day 05 completion review found that missing Prometheus metrics could be reported as zero errors, malformed or Pending/init-failing pods could be misclassified, and partial command matching could accept ambiguous scale requests. This change preserves unknown health states, validates pod data, requires an exact scale command and kills/reaps timed-out kubectl processes. Slack intake now bounds the body before signature verification, validates event fields, limits enqueue time and exposes meaningful readiness.

The local bot provides three read intents through API/Kubernetes MCP/Prometheus MCP, structured audit, a durable Redis inbox and a separate identity for scaling only insighthub-api. Scale requires a one-use 60-second approval bound to workspace, channel, thread, approver and deployment state. Destructive requests are denied. No API, ingestion, schema or verifier changes are included.

## Validation

- 34 tests pass: 25 bot tests and 9 milestone contracts. Ten regression cases failed on the previous implementation. Ruff, Mypy, pre-commit and Docker build pass.
- Microsoft Edge Computer Use on real Slack covers health/ingestion/pods, destructive denial, approval with no early mutation, scale 1 -> 2, replay/expiry denial and restore to 1/1. A failing pod and unavailable Prometheus are detected; both faults are restored.
- Live HTTPS probes verify signature/timestamp rejection, a valid challenge and the 64 KiB request limit.
- API upload -> ready -> chat/citation in Edge passes using the configured real provider. The browser file chooser remains unverified because the Edge extension requires Allow access to file URLs.
- Push CI and PR CI each passed local-baseline and chatops-day5. The verifier passes its partial-runtime-contract; it does not certify the whole milestone.
- A 179.93-second local MP4 records actual Edge Slack interaction in six sequential screen-capture segments. Loom submission is pending permission to access the account.

## Evidence and handoff

[Current evidence](../evidence/day5/20260929/Runtime_Validation.md), [self-check](Self_Check.md), and [review findings](Review_Findings_20260929.md). The draft PR targets day4-observability because remote main is at Day 03. The baseline must land before this PR can target main cleanly. Keep the PR draft until the pending submission/UI checks are resolved. The lab runs one queue worker; a production Kubernetes bot deployment is outside this scope.
