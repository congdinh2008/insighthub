Title: feat(day6): enforce LLM security, budget controls and FinOps

InsightHub now checks user input, retrieved chunks and model output, and routes app, ChatOps and coding through budgeted LiteLLM identities. The isolated Day06 overlay supports paired API/worker rollback. Mandatory gateway checks fail closed when policy/accounting is unavailable; unresolved charges and native/ledger discrepancies remain visible and alertable.

Validation:
- [Release live CI 36843076783](https://github.com/congdinh2008/insighthub/actions/runs/36843076783), source 711f20f: final and independent replay each 164/164 PASS, including 20/20 benign. All 86 pytest tests passed with zero failures/errors/skips; all nine budget probes passed. Baseline reproduced 132/164 with 32 oracle failures and no execution errors.
- Second-run recorded cost USD 0.19936694; zero unresolved admissions in that run. The separately authorized first run recorded USD 0.187197 and one unknown charge; it is retained as INCOMPLETE after a guard-unavailable 503. Both runs were individually capped at USD 0.50. Live SHA flag removed; automatic live schedules remain OFF.
- Frozen local final/verifier each passed 164/164, with real Edge upload, policy/recovery, Slack and Grafana evidence. Runtime/DB/ChatOps regressions are documented in the evidence matrix.
- CI reporting no longer republishes a stale local budget JSON. Public follow-up contains reviewed aggregate results, artifact hashes and masked UI evidence; new raw CI artifacts/logs remain local and in Actions (7-day retention).

Known limits: guard overhead p95 10.804s exceeds the candidate 3s target; chat p95 12.494s meets 15s. Historical local native accounting is missing USD 0.0004324 and 148 admissions have unknown provider charge. These are not erased by the successful CI run. Browser policy blocks local HTML report rendering. Semantic cache, adaptive routing and fallback remain OFF; AWS is N/A. See [Release_Readiness](Release_Readiness.md) and [Self_Check](Self_Check.md).

The final follow-up commit changes documentation/evidence only; runtime source and the frozen dataset remain identical to the successful release CI. Merge after required checks on that commit pass.
