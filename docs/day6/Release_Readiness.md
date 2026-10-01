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
- GitHub Environment `day6-model-evaluation` now requires the repository owner's review; the approved ZenLayer key is stored as an encrypted Environment secret. No live SHA has been authorized yet; no CI model charge incurred at this step.
- Public push/PR remains pending explicit payload confirmation after automatic approval review rejected publication of the evidence bundle. Code/evidence remain local until that confirmation.
