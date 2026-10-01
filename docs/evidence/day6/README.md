# Day06 evidence index

Nguồn nghiệm thu: source commits `98c5faa`, `8dee0fa`, `e575ae6`, `333af26`, `101094a`, `3db6ead`, `37d45c1`, `3372d90`, `a9eab4d`, local kind, ZenLayer, ngày 29/09-01/10/2026. Xem [Self_Check](../../day6/Self_Check.md), [runtime matrix](Runtime_Validation.md) và [runbook](../../day6/Runbook.md). Không suy kết quả final từ tên folder; đọc trạng thái/record count bên trong.

## Các lượt red-team

| Folder | Ý nghĩa |
|---|---|
| `initial/` | Lượt trước fixes:164 executed,98 pass,66 strict-v1 failures,0 errors. Không gọi toàn bộ strict failures là vulnerability |
| `enforced-iteration1/` | 163 records,1 measurement error; INCOMPLETE, không dùng làm acceptance |
| `enforced-iteration2/` | Exploratory164/164pass; helper source thay đổi trong lượt, không phải source-frozen acceptance |
| `baseline-finalsource/` | Baseline tại source trước fix8dee0fa;164 executed,132 pass,32 fail,20/20 benign; retained lịch sử |
| `enforced-single-choice-review/` | Dừng chủ động sau 121 records pass để fix completion choices; INCOMPLETE |
| `baseline-contaminated-incomplete/` | Dừng sau 46 records vì còn attack fixtures từ lượt bị gián đoạn; cleanup exact IDs/hashes được lưu, không dùng làm acceptance |
| `baseline-before-budget-fix/` | Source333af26:164 executed,132 pass,32 fail,20/20 benign; giữ nguyên lịch sử |
| `final-before-budget-fix/` | Source333af26:164/164 pass,20/20 benign,120 blocked/44 released; lịch sử |
| `verifier-budget-race-failed/` | Source333af26:164/164security cases pass nhưng overall FAIL ở budget probe do chưa flush spend; raw results retained |
| `baseline-startup-incomplete/` | Source101094a:14 startup connection errors,150 records; INCOMPLETE, preserved; preflight fixed to require /readyz before starting |
| `baseline-before-capability-fix/` | Source101094a:164 records,131 pass,32 attack failures và1 benign keyword failure,0 HTTP errors |
| `final-before-capability-fix/` | Source101094a:164/164pass,20/20benign; lịch sử |
| `verifier-oracle-inconsistent-incomplete/` | Source101094a:52records; gen-016 grader false label với rationale an toàn; dừng chủ động, không gọi là external side effect |
| `baseline-interrupted-20260929/` | Source3db6ead:112/164records, bị gián đoạn; raw records giữ nguyên |
| `baseline-provider-expired-incomplete/` | Lượt ngày 01/10 bị upstream key hết hạn; raw lỗi giữ nguyên, không dùng nghiệm thu |
| `baseline-before-scope-policy-fix/` | Source37d45c1: 164 probes,131 PASS,33 failures,20/20 benign; raw history |
| `final-before-scope-policy-fix/` | Source37d45c1: 161 PASS,1 benign scope-label failure,2 safe503 timeouts; INCOMPLETE |
| `baseline-evaluator-500-incomplete/` | Source3372d90:163 rows,130 PASS,33 oracle failures,1 evaluator HTTP500; all20 benign PASS |
| `baseline-single-choice/` | Source a9eab4d: 164 executed, 132 pass, 32 fail; benign 20/20; 0 target HTTP errors; evaluator retry details retained |
| `final/` | PASS: 164/164, benign 20/20; 125 blocked/39 released, source/dataset unchanged |
| `verifier/` | PASS: 164/164 fresh cases + 80 pytest tests; actual observations/JUnit retained |

SHA-256 dataset: `74c9ea50f65255b62c3cb643c347dea0dc02078458c75ae9a54b45995ebf2ef6`.
SHA-256 verifier source: `c49623b4b2600af16d9e01e01f0b2c1c95afc9e88e30eae03df712fc6593dd8d`.
`start.json` còn ghi thêm gateway/deploy file hashes ngoài source roots mặc định của verifier.

Mỗi scan hoàn chỉnh giữ Promptfoo raw JSON/HTML, `results.jsonl`, eval/cost envelopes. Oracle-v2 cho phép public facts, chấm semantic tất cả released attack answers và kiểm forbidden markers trên full response. Calibration ở `judge-validation.json`. Historical v1 giữ nguyên để audit; không rewrite kết quả cũ theo oracle mới.

## Runtime artifacts

- Identity/budget: `gateway-auth.json`, `gateway-budget.json`, `key-lifecycle.json`, `gateway-route-cost-controls.json`, `budget-reallocation.json` (tổng caps không tăng).
- Guard, direct key và recovery: `guard-live.json`, `direct-provider-access.json`, `fault-*.json`, `rollback.json`, `embedding-budget-retry.json`.
- Ba workload: Edge upload/chat + Slack summaries/scale + `coding/` patch/tests. Request attribution đầy đủ trong `runtime/gateway-ledger.jsonl` sau đối soát.
- FinOps: pricing screenshots, `prompt-cache.json`, `budget-alert.json`, Grafana screenshots, `runtime/cost-reconciliation.json` và cost report.
- UI: các ảnh `edge-*.png`, `slack-*.png`, `grafana-*.png`; tài liệu UI synthetic được cleanup đúng own IDs.
- Regression: `regression/` lưu logs chọn lọc; phạm vi test và giới hạn trong runtime matrix.

`base-override-before.json`, `route-override-before.json`, `override-probe.json` là negative probes trước khi xác nhận LiteLLM native controls. Không phải bằng chứng caller đã override route, price hoặc mock completion thành công.

Secrets/runtime credentials, kubeconfig, Slack IDs thô, tunnel URL không thuộc deliverable. Chỉ commit metadata đã lọc, synthetic test content và ảnh UI đã kiểm tra. Không có provider invoice; mọi USD là estimate từ actual usage và pricing catalog quan sát trong lượt lab.

## Kết thúc nghiệm thu local

- `edge-final-upload.json`, `edge-final-fixture.md`, `edge-upload-chat-final.png`, `edge-capability-final.png`, `edge-scope-recovery-final.png`: fresh Edge upload, grounded citation, scope và policy recovery trên source a9eab4d; test document được cleanup.
- `latency-concurrency2.json`: 40/40 expected answers, chat p95 12.494s đạt 15s; paired overhead p95 10.804s chưa đạt 3s.
- `handoff.json`: readiness, queue, cap, remaining reserve và alert thực tế; P7 OFF, AWS N/A.
- `runtime/` là snapshot sau mọi paid calls; `runtime-after-acceptance/` giữ snapshot trước latency/UI.
- [Cost_Report](Cost_Report.md) nêu native evaluator gap 0.0004324 USD và 148 admissions có charge unknown; không gán phí bằng 0.
- Verifier scope `partial-runtime-contract`, `milestone_complete=false` giữ nguyên. [Self_Check](../../day6/Self_Check.md) bổ sung review đầy đủ các MH; UI-08 và remote CI không được tính PASS.

## GitHub release follow-up

- [Release_Readiness](../../day6/Release_Readiness.md) and `release/ci-run-summary.json`: PR #25, exact-head live run 36838215597, baseline 132/164, final 164/164, independent replay INCOMPLETE at benign-11 (HTTP503). CI cost USD 0.187197 plus one unknown charge; no fresh CI budget probe evidence.
- Raw CI artifacts and failed-step log are retained in the local ignored `release/ci-run-36838215597/` folder and the GitHub Actions artifact (7-day retention), outside this public follow-up commit. Its `ci-runtime/gateway-budget.json` is a copied historical local file, explicitly not fresh CI evidence.
- `release/ci-source-verification.json`: CI source matches clean committed checkout. `post-live-source-delta.json` identifies the separate reporting-only fix.
- `release/virtual-keys-masked.png`, `accounting-alerts-fired.json`, `github-release-controls.json`: masked UI, actual firing alerts and protected release controls.
