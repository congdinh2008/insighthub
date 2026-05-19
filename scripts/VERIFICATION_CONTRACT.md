# InsightHub verification contract v2

The starter deliberately leaves the running project unfinished. The authoritative
assignment is [Specification v3.2](../Running-Project-Specification-Student.md).
This verifier checks a bounded subset of its requirements, not full grading,
production readiness or independent attestation.

## Commands

```sh
python3 scripts/verify.py                         # starter structure only
python3 scripts/verify.py setup                   # local tools + Compose validation
python3 scripts/verify.py smoke --api-url http://localhost:8000 --web-url http://localhost:3000
python3 scripts/verify.py fingerprint             # current content, including dirty edits
python3 scripts/verify.py day1 --evidence-dir evidence # async worker is mandatory
python3 scripts/verify.py day3 --ci-repo owner/repo --ci-run-id NUMBER --evidence-dir evidence
python3 scripts/verify.py day7 --evidence-dir evidence --json
python3 -m unittest discover -s tests -p 'test_verify*.py' -v
```

Shell wrappers forward arguments. `0=PASS` means the implemented subset passed;
`1=FAIL` is an observed failed assertion; `2=INCOMPLETE` means missing, stale,
unsupported, fixture-only evidence or unavailable dependency.
Day reports have `scope=partial-runtime-contract`,
`specification_review_required=true` and `milestone_complete=false`.
Starter/setup PASS does not establish runtime completion. Day 7 retains
INCOMPLETE even when all automated subsets pass until a trainer reviews the full
specification. The script does not issue or store that academic approval.

`--extended` is a compatibility alias only: Day 1 always requires async upload,
worker ingestion and retry/idempotency scenarios. Day 3 defaults to GitHub CI.
`--ci-profile local` is preparation and remains INCOMPLETE for Day 3.
Day 5 defaults to HTTP signature verification; Socket Mode is an additional
transport, not permission to omit HTTP-signature learning/tests or live Slack.

## Coverage and remaining review

| Day | Artifact roles consumed by this helper | Automated subset | Full specification review still required |
|---|---|---|---|
| 1 | refactor, review, worker, worker_dockerfile | Refactor/invalid input tests, async 202, bounded ready polling, running worker and correlated log, retry/idempotency tests | Five components, context six sections, PR, prompt logs, latency workload and quality rubric/feature |
| 2 | mcp_manifest | Official SDK tests and real backend invocation of the supplied InsightHub MCP example | Four separate Filesystem/container/K8s/Prometheus MCP integrations, connections/calls, RBAC/allowlists, Inspector, debug case and quiz |
| 3 | deployment, ci_binding | Policy tests, Terraform validation, Checkov, recent GitHub run and source binding | Full fmt/lint/scan/policy/plan/cost/apply pipeline, OIDC, AWS module/resources, Helm LIVE/HTTPS, smoke and teardown |
| 4 | rca, rca_2, rca_3, rules, rule_tests, dashboard, mlops_notes | Three distinct incident IDs and cited live samples, promtool, at least nine panels with query targets, nonempty notes | All five component signals, three scenarios/rules, baseline, Alertmanager to Slack, panel meaning, RCA reasoning and MLOps quiz |
| 5 | permissions, audit | Permission/approval/dedup tests, correlated audit and HTTP signature/health by default | Actual Slack three intents, MCP reuse, durable ACK/queue/retry, distinct mutation identity, valid/invalid timestamp handling, screencast |
| 6 | dataset, eval_initial, eval_final, cost | Injection/benign/budget tests, per-case provenance and cost arithmetic | Promptfoo 50+ coverage, actual uploaded/retrieved poisoning, runtime guardrails, LiteLLM routing and three virtual keys, concurrent budget behavior, dashboard/threat model, AWS Budgets when AWS used |
| 7 | No separate envelope | Aggregates six partial verifiers without promoting fixture or missing evidence | All artifacts, required screencast/self-evaluation/cost report, original showcase format and eight-dimension rubric |

The Day 2 starter contains only example tools; passing it does not satisfy the
four-server assignment. The Day 6 JSON format below is a normalized evidence
format, not a substitute for Promptfoo native configuration and reports.

## Evidence envelope

`evidence/dayN.json`, UTF-8 JSON, no commands:

```json
{
  "schema_version": 1,
  "day": 1,
  "mode": "real",
  "observed_at": "2026-09-08T16:30:00Z",
  "source_sha256": "<digest from fingerprint>",
  "artifacts": {
    "refactor": {"path": "api/app/routers/documents.py", "sha256": "<file SHA-256>"},
    "review": {"path": "evidence/day1-review.md", "sha256": "<file SHA-256>"}
  }
}
```

All artifact paths are relative to the repository and must remain inside it after
resolving symlinks. Empty files, known starter dummy content, malformed JSON and
hash mismatches are rejected. No subprocess arguments, Python, shell commands or
MCP server commands are read from this envelope. Extra fields are data, not code.
Default maximum age is 24h (`--max-age-hours`), future tolerance 60s. `fixture`
mode can exercise offline contracts but always leaves the milestone INCOMPLETE.
For Days 1-5, envelope `real` means actual software/test/runtime execution; the
application may use a fixture LLM, and that does not prevent the implemented subset from passing. Full assignment evidence remains required.
Only Day 6 `real` additionally requires real-model evaluation provenance. MCP
uses a separate transport field: envelope real maps to SDK backend_mode=live
and live=true; envelope fixture maps to backend_mode=fixture and live=false.

The source digest covers source/config/test files in api, web, ingestion-worker,
chatops-bot, infra, observability, security, tools, scripts, tests and .github,
plus root Compose files, dependency/config files and .env.example. It excludes
build/cache/vendor outputs, reports and actual .env secrets. It does not depend
on HEAD, file mtime or a clean working tree. Save evidence after source changes
settle. A release ZIP has its own whole-file SHA-256; store both this digest and
source_sha256 in the release manifest. A ZIP digest does not attest runtime.

## Day requirements

Install optional milestone Python dependencies in your test environment with
`python3 -m pip install -r scripts/requirements-verification.txt`. The default
starter and verifier regression tests use the Python standard library only.

Days 1, 3, 5 and 6 student test suites are at `tests/milestones/dayN/test_*.py`. They are
student deliverables, not included solutions. The verifier invokes pytest itself,
in a temporary working directory, with its cache disabled and JUnit output in
/tmp. Tests use INSIGHTHUB_REPO_ROOT, INSIGHTHUB_API_URL, INSIGHTHUB_WEB_URL,
INSIGHTHUB_BOT_URL, INSIGHTHUB_BOT_TRANSPORT, INSIGHTHUB_KUBE_CONTEXT and INSIGHTHUB_NAMESPACE. Dependency
imports should use INSIGHTHUB_REPO_ROOT. Unit tests must not send real Slack messages; live workspace evidence is collected separately as required by the assignment. Unit tests
exercise permission/approval/dedup with isolated transport doubles. The verifier
requires named scenarios, actual collected tests, no skips/xfails and exit 0.
Test source and local reports remain reviewable student evidence, not a trusted
external witness. Live probes provide additional observations.

Day 2 uses the actual SDK module maintained under `tools/mcp`, manifest
`tools/mcp/manifest.json`. Install dependencies with
`npm ci --prefix tools/mcp --ignore-scripts` (Node 22+). Offline integration:
`node tools/mcp/smoke.mjs` plus `npm --prefix tools/mcp test`. Milestone live:
`node tools/mcp/smoke.mjs --live`. The verifier invokes fixed Node paths,
not manifest install/test/smoke arrays. It checks real SDK calls, supported
manifest tools, all executed test results and explicit `backend_mode`/`live`.
Fixture SDK checks pass the offline test layer but do not attest a real backend.
Use `--mcp-tools insighthub_health,insighthub_list_documents`; optional
`prometheus_summary` requires `--prometheus-url`. This module intentionally
supports loopback backend URLs only; remote endpoints are outside its contract.
Four MCP integrations remain mandatory for Day 2; this helper checks only the supplied SDK example.

Day 1 uses `--docker-context`, `--compose-file`, `--compose-project`,
`--worker-service` (default ingestion-worker). A worker JSON log event has
`event="ingestion_completed"`, `document_id` equal to the freshly uploaded id,
`timestamp` in RFC3339, and `status="ready"`. The log is fetched by the verifier
from the selected running container after upload. Emit this event as part of the
student implementation; supplying a saved log alone is insufficient.

Day 3 defaults to `--ci-profile github`. Preparation with `--ci-profile local` checks: current policy tests and Terraform
fmt/init/validate plus Checkov run locally. Terraform runs from an isolated
copy in /tmp with backend disabled. Provider downloads may need network access;
no AWS account, cloud resource deployment or GitHub account is required. Missing
local tools are INCOMPLETE. ci_binding JSON has `source_sha256` and
`artifact_sha256` (SHA-256 of the deployment artifact). This validates integrity
and fresh policy/test execution; it does not independently prove a locally
supplied artifact was built from that source. Review the artifact-producing test
and source binding. A clean HEAD is never required.

The default `--ci-profile github --ci-repo owner/repo --ci-run-id NUMBER` additionally
fetches that successful recent run and artifact `verification-source`, containing
`source-manifest.json` with matching `source_sha256` and `artifact_sha256`. An
unrelated green run or HEAD-only match cannot attest dirty source. Deployment
health is not attested by either profile. Store report/binding JSON and build
archives under evidence/ to avoid source-digest self-reference.

Day 4 requires `--prometheus-url URL`, three distinct RCA artifacts (`rca`, `rca_2`, `rca_3`), `mlops_notes` and a dashboard with at least nine query panels. Each RCA JSON contains `incident_id`,
`started_at`, `ended_at`, `hypotheses` (nonempty text list), `samples` (nonempty
list of `{metric, labels, timestamp, value}`). `metric` is a Prometheus metric
name, `labels` a string mapping, timestamp RFC3339, value finite numeric.
Every cited sample must fall inside the incident window and match a live query
range sample. Dashboard panels must contain actual nonempty `targets[].expr`.
Rules and their tests are parsed with safe YAML, require executable rule expressions,
nonempty input series and expected assertions, and are passed to promtool.
The rule test file must reference the submitted rule artifact; no keyword grep.

Day 5 audit JSON contains `run_id`, `events` with `timestamp`, `event_id`,
`action`, `decision` (allowed/denied/approval_required), `user`, `test_run_id`.
Tests receive a fresh INSIGHTHUB_VERIFY_RUN_ID and must emit audit for that run.
The verifier requires denied and approval_required events for that run. The
artifact hash is checked before running tests; write new test observations to
INSIGHTHUB_VERIFY_OBSERVATIONS (a /tmp path) as `{run_id, events}`. Saved audit
is provenance and must also be valid; it is not sufficient to pass runtime.

Day 6 dataset JSON: `{cases:[{id,category,input,expected}]}`, categories must
cover `injection` and `benign`. Reports: `{mode,observed_at,source_sha256,
dataset_sha256,results:[{case_id,passed,severity,provider,model,request_id,
input_tokens,output_tokens}]}`. Initial and final must both cover the exact
nonempty dataset with unique IDs. Final must have every case passing; severity
is one of low/medium/high/critical. Real mode requires non-placeholder provider,
model and request_id for every result; hash/extractive/mock/fixture are
not real model provenance. Ollama is a real model provider and is valid. Cost: `{mode,observed_at,source_sha256,currency:"USD",
entries:[{request_id,input_tokens,output_tokens,input_usd_per_million,
output_usd_per_million,cost_usd}],total_usd,budget_usd}`. Entries must cover final
report requests exactly, token counts match, cost arithmetic matches and total
is within declared positive budget. Real zero-provider-cost entries (including
Ollama or free-tier calls) require `resource_usage` with `measurement_source`,
positive `duration_seconds` and positive `memory_peak_bytes`. Power usage and
operating cost are not assumed to be zero. No commercial provider is required. Student tests also write fresh observations
`{run_id,eval_final,cost}` to INSIGHTHUB_VERIFY_OBSERVATIONS; reports alone cannot
pass. This is local test evidence; provider billing attestation and effectiveness
of the dataset still require review.

## Host portability (starter 0.2.3 / spec v3.3)
Mỗi học viên chọn một host Claude Code/ChatGPT-Codex/Antigravity. scripts/check-agent-setup.py --host --config kiểm tra sáu headings, 200 dòng, JSON/TOML và transport fields cơ bản; PASS chỉ là static shape, milestone_complete=false, host_verified=false. Không chứng nhận nội dung TODO, config schema đầy đủ, bốn backend, connection, RBAC hoặc tool call.

Fingerprint bao gồm AGENTS.md, CLAUDE.md, specification, workspace rules và config MCP project nếu có. Không đọc config user ngoài repo. Sửa các nguồn này làm evidence cũ hết khớp và phải xác minh lại; không sửa source_sha256 bằng tay để tái sử dụng kết quả cũ. Config nộp phải loại secret.

Day 6 giữ ba workload InsightHub/bot/coding workflow. Coding host chính có thể route trực tiếp hoặc thực thi workflow API theo mục 0.5 của spec; không bắt host thứ hai. Automated day verifier vẫn chỉ là partial contract, trainer kiểm tra cả ba key/budget/trace và phạm vi thật.
