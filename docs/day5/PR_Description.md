# feat(day5): add bounded Slack ChatOps bot for InsightHub lab

The Day 05 Slack app previously had a placeholder `/slack/events` endpoint. This change verifies Slack request signatures, durably queues mentions before ACK, and replies to three fixed operational questions using InsightHub, Kubernetes MCP and Prometheus MCP data. The ingestion answer explicitly counts documents created today in ICT that are currently ready; it does not claim first-completion semantics.

The only write action is scaling `insighthub-api`. A one-time, 60-second approval bound to the workspace, channel, thread, approver and deployment state is required before the separate scale identity can execute it. Destructive and unsupported requests are denied. The lab includes structured audit, Redis recovery/dedup, scoped RBAC, local cloudflared runbook, bot tests, Day 05 milestone tests and a CI job. No application business code or schema changes are included.

Validation: bot suite 4/4, milestone suite 6/6, Ruff/Mypy, Docker build, Day 05 verifier and upload -> ready -> chat regression smoke all pass. Live Slack evidence covers all three reads, destructive denial, approval/scale/replay/restore and one Zenlayer summary. The verifier intentionally reports partial-runtime-contract. The 3-minute screencast and remote CI run remain pending; see `docs/day5/Self_Check.md` and `docs/evidence/day5/Runtime_Validation.md`.

Proposed base: a remote branch containing local Day 04 merge commit `7613ba0`. Current remote `main` is `1dfa6b7` (Day 03), so opening against it now would include Day 04 changes outside this PR's intended scope. GitHub CLI auth also needs renewal before pushing/opening the PR.
