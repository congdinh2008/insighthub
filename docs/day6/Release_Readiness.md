# Day06 - Release follow-up, 01/10/2026

User scope: finish necessary local acceptance, create PR and merge main; semantic cache, adaptive routing and fallback remain OFF. One GitHub real-model evaluation authorized up to USD 0.50; automatic live schedules remain disabled.

## Changes after local acceptance

- Unknown-charge metric now includes admissions unresolved for at least 120 seconds, deduplicated by workload/request ID. An upstream failure callback is not evidence of a zero provider charge. Active requests within the grace window are not counted prematurely.
- Added persistent accounting-delta and unresolved-charge alerts. The historical missing native evaluator row remains disclosed; native counters and old evidence are not rewritten.
- CI live requires protected environment approval plus the exact authorized head SHA. Schedule runs offline boundaries only. Ephemeral key caps total USD 0.40, ledger watchdog stops at USD 0.35 with USD 0.15 reserve within the authorized USD 0.50 envelope. Native caps remain soft.
- CI repeats baseline, final and independent live pytest acceptance on the same frozen source/dataset, retaining raw reports, JUnit, ledger and budget probes. Failed/incomplete stages are retained.

## Explicit remaining limits

- Guard overhead p95 10.804s exceeds the candidate 3s target; total chat p95 12.494s meets 15s. Inspection found sequential model-backed checks at API input/context/output and gateway input/output. Removing these checks or switching policy/model without new validation would weaken the tested boundary. No threshold or assertions are relaxed for release. This is a performance follow-up, not a missing Day06 Must-have feature.
- Historical native evaluator gap USD 0.0004324 and 148 unresolved admissions remain subject to provider billing reconciliation. The exporter now exposes the unknown state instead of showing zero. No invoice has been supplied.
- Edge local HTML navigation remains blocked by the browser tool policy. Raw HTML/JSON and real app/Slack/Grafana UI evidence are retained. No alternate route is used to bypass that rejection.
- Old local evidence retains its original source fingerprint. The release CI reports identify the later source; do not relabel historical artifacts.
- AWS N/A. No claim of Level 4, all-OWASP coverage, hard native budget caps or production HA.

## Local follow-up results

- 82 offline Day06 tests PASS, Ruff PASS. Two exporter tests fail against the unmodified old exporter in an isolated temporary directory, and pass against the fix. No intentionally failing test was added to the PR branch.
- Initial test collection lacked prometheus-client in the local Day06 venv; installed the exact version/hashes already present in requirements-dev.txt. The failed log is preserved separately; the CI workflow installs this full lock file.
- Prometheus reports 148 unresolved charges: app 16, guard 2, evaluator 130; accounting endpoint available=1. Exact native evaluator delta remains USD 0.0004324.
- GitHub Environment `day6-model-evaluation` now requires the repository owner's review; the approved ZenLayer key is stored as an encrypted Environment secret. Exact head `60ebb4d1271f222fa72fed62fd44937160468f08` was authorized for CI run `36838215597`; the SHA flag was removed immediately after Environment approval so future live jobs remain disabled.
- User explicitly confirmed publication of the sanitized evidence bundle on 01/10/2026. PR [#25](https://github.com/congdinh2008/insighthub/pull/25) is open. Main now requires local-baseline, chatops-day5 and boundaries with strict up-to-date checks and admin enforcement. The earlier rejection is resolved by that confirmation.

## Submission UI and CI scope

- `docs/evidence/day6/release/virtual-keys-masked.png` shows all three workload keys and both service keys active in the real LiteLLM UI. Tokens remain masked, no credential copy/reveal was used, and the admin session was logged out after capture. LiteLLM 1.103.0 rounds the list's budget display to whole dollars; authoritative exact caps are in `handoff.json` and native API evidence, not that rounded label.
- Persistent mismatch alert and all three unknown-charge alerts reached firing; see `release/accounting-alerts-fired.json`.
- Day03 workflow was inadvertently triggered because its existing `deploy/**` filter includes Day06 Compose. Run `36838215583` was cancelled at AWS credential setup before Terraform plan. Its completed static/application checks passed; no cloud apply or AWS runtime acceptance is claimed. Day06 live CI uses ephemeral Docker Compose on GitHub-hosted infrastructure, not AWS services.

## CI artifact provenance correction

- Review found that the runner copied the existing local `gateway-budget.json` even though live pytest does not export its returned budget rows. Run 36838215597 retains that raw copied file as historical evidence, not as fresh CI measurements. The live shared fixture subsequently failed at benign-11, so the CI budget probes did not run. The copied JSON remains the earlier local budget evidence only.
- The follow-up runner removes that misleading copy, explicitly labels the budget evidence scope and enables pytest stdout so future runs retain the nine probe lines. The added regression rejects publication of historical budget JSON. All 83 offline tests and Ruff pass. This reporting-only change is after the approved live-run SHA; application, guard, gateway and test assertions used for real-model acceptance remain unchanged. No second paid run was started.

## GitHub real-model replay

- Run [36838215597](https://github.com/congdinh2008/insighthub/actions/runs/36838215597), source commit `60ebb4d1271f222fa72fed62fd44937160468f08`.
- Baseline: 164 executed, 132 PASS, 32 oracle failures, 0 execution errors (11m52s).
- Enforced final: 164/164 PASS, 0 failures, 0 execution errors (10m59s). Independent live pytest is INCOMPLETE: 154/164 returned PASS (10/20 benign), then benign-11 hit HTTP503 guardrail_unavailable. JUnit: 82 PASS, 3 setup errors, 0 assertion failures. Budget probes did not run.

- Recorded CI cost: USD 0.187197, within the USD 0.50 envelope; one admitted guard request has unknown charge. The ledger ends with a guard request lacking completion and an app guardrail_unavailable error roughly 15 seconds later. This is consistent with guard/provider timeout; no provider invoice or completed upstream response establishes its precise cause/charge. The boundary failed closed.
- Clean git archive of 60ebb4d reproduces CI fingerprint `0e410f574e91249c2e86408ff15836ed715467adc707945a55220e9408090fa3`. Local ignored host configuration/state explains the workspace fingerprint difference; no private configuration/state is published.
- Merge remains blocked on the incomplete live acceptance. A second paid run is NOT authorized by the original one-run approval and has not been started. Exact-head flag remains absent. Prepared follow-up is the same frozen corpus/runtime with only the reporting fix, full baseline/final/independent replay under the existing USD 0.50 cap, pending user approval.

- Public follow-up contains aggregate results, source hashes and reviewed masked UI evidence. The newly downloaded raw CI artifacts/ledger/failed-step log remain local and in the GitHub Actions artifact (7-day retention); public push of that additional raw bundle was rejected by automatic approval review. No raw payload is included in the follow-up publication.
