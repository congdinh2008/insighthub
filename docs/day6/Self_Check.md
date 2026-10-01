# Day 06 - Self-check và phạm vi nghiệm thu

Source implementation kết thúc ở `a9eab4d` trên branch `day6-security-finops`; ngày 01/10/2026. **Must-have local đã có evidence, AWS N/A.** Final và fresh verifier đều 164/164 cases PASS, benign 20/20; verifier 80 tests PASS, không skip. Fingerprint `c49623b4b2600af16d9e01e01f0b2c1c95afc9e88e30eae03df712fc6593dd8d`. Giữ optional P7 OFF theo xác nhận của anh. UI-08 mở HTML và remote CI/publication còn giới hạn riêng phía dưới.

## Must-have

| MH | Trạng thái hiện tại | Evidence |
|---|---|---|
| MH1 config Promptfoo | Implemented, pinned 0.123.1 | `security/promptfooconfig.yaml`, package lock |
| MH2 coverage | 164 frozen cases, đủ 5 attack groups và 20 benign | `security/coverage.md`, dataset SHA trong reports |
| MH3 initial | 164 executed, 98 pass, 66 strict v1 failures, 0 errors | `docs/evidence/day6/initial/`; không gọi 66 failures là 66 vulnerabilities |
| MH4 fixes | Source `a9eab4d` và các commits tiền nhiệm, boundary tests và findings ledger | `security/findings.md`, API/gateway/NeMo/bot changes |
| MH5 final | PASS: 164/164, benign 20/20; 125 blocked/39 released | `docs/evidence/day6/final/`, `verifier/result.json`, actual observations/JUnit |
| MH6 guardrails | Live input/context/output block, benign, Unicode, failure/recovery | `guard-live.json`, `fault-guard.json`, Edge images |
| MH7 gateway | LiteLLM/DB/ledger deployed, restart/accounting failure tested | `fault-gateway.json`, `fault-accounting-db.json` |
| MH8 three keys | App/bot/coding model calls thật; ACL, revoke/expiry, budget sequential/concurrent | `gateway-auth.json`, `gateway-budget.json`, `key-lifecycle.json`, coding/Slack evidence |
| MH9 app gateway | Chat + embeddings qua virtual key; upstream key absent | `direct-provider-access.json`, isolated DB/index/queue |
| MH10 FinOps | 15-panel dashboard deployed, threshold alert firing/resolved | `observability/day6/llm-cost.json`, `budget-alert.json`; `grafana-cost-final.png`, `grafana-prometheus-reconciliation.json`, [Cost_Report](../evidence/day6/Cost_Report.md) |
| MH11 AWS budget | N/A | `aws_used=false`, không tạo AWS resources |
| MH12 threat model | 12 threats với mitigation/test/owner/residual risk | `security/threat-model.md` |

## E2E và regression đã chạy

- Edge file chooser upload benign, ready, grounded answer/citation; direct injection block và benign recovery.
- Edge poisoned upload: exact document/chunk SHA verified; unsafe chunk không xuất hiện trong contexts hoặc answer, chỉ trả safe guide. Own test document đã cleanup.
- Edge budget exhausted/recovered và guard unavailable/recovered có ảnh riêng.
- Slack ba reads có AI summary thật; hết budget vẫn trả facts và báo summary unavailable. Scale 1 -> 2, confirm, replay denied, restore 1. Injection/destructive request bị deterministic deny. Wrong-user/thread/expiry là integration coverage, không nhận có live Slack user thứ hai.
- Coding workflow trả patch thật, validator kiểm exact path, immutable tests chạy non-root/read-only/network disabled. First failed patch được ghi nhận; second attempt passed.
- Native key lifecycle: missing/invalid denied; auth expiry khoảng 6 giây, revoke khoảng 45 ms trong phép thử. Đây là auth endpoint probe; workload generation được chứng minh riêng.
- Budget: cả ba keys có allow/deny ở concurrency 1/2/5; overshoot đo được, không claim hard cap. Accounting/gateway/guard faults phục hồi; rollback/reapply API/worker pair đạt, giữ cả PVC cũ và mới.
- Backend 76 tests + 71 subtests với random DB schema, zero skip; Day06 77 boundary tests; ChatOps 39 tests; 68 verifier contract tests; Day02 14 tests; Day03/04 10 tests; MCP 22 tests và protocol smoke. Ruff/Mypy strict API-worker, Mypy bot passed. Full live Day06 verifier: 80 tests PASS, không skip; contract tự động được bổ sung bởi MH/UI/FinOps review.
- ACK signed duplicate requests qua actual HTTP intake/Redis dưới 0.006 giây; không suy ra Slack network end-to-end latency từ số này. Fresh queue semantics có integration tests.

## Should-have và giới hạn

| Hạng mục | Kết quả / quyết định |
|---|---|
| PII input/output | Implemented và live synthetic checks passed; regex conservative, không claim nhận diện mọi PII |
| Provider prompt caching | Native usage xác nhận: 4/4 answers đúng, warm 1792/1846 cached tokens, cost ước tính 0.0002056 thay 0.0007432 USD/call; xem `prompt-cache.json` |
| PR/nightly | Workflow code và protected-environment/fork restrictions có; remote chưa chạy do quyền publish Day06 đang chờ. Live credentials chưa provision lên GitHub |
| Semantic cache / adaptive routing / fallback chain | OFF theo xác nhận của anh ngày 01/10/2026. Optional package P7 không thuộc scope nghiệm thu Must-have lượt này |
| HTML reports trong Edge | Navigation `file://` bị browser tool URL policy chặn. Upload permission vẫn hoạt động. Raw HTML/JSON được giữ và kiểm trực tiếp; không claim rendered report UI PASS |
| Network isolation | Kind CNI chưa chứng minh egress enforcement; chỉ chứng minh app không có provider/master keys và unauth direct call denied |
| Billing / judging | Catalog estimate, chưa có provider invoice. Judge cùng model family, probabilistic. No-HIGH chỉ trong corpus/deployment đã test |
| Local resources | Docker VM khoảng 4 GiB; build/scan tuần tự, baseline và Grafana có thể tạm pause để tránh memory pressure. Runtime cuối phải restore Grafana và app replicas 1 |

Không claim Level4, production HA, legal compliance, AWS runtime hoặc all-OWASP coverage. UI-08 không được tính PASS; remote CI chưa chạy. Các optional bị tắt không thuộc scope nghiệm thu Must-have.

## Trả lời chín câu self-check của specification

1. Final no-HIGH/CRITICAL trong frozen corpus đã được xác nhận ở cả final report và fresh verifier. Initial v1 có 66 strict failures, còn baseline v2 trên frozen source a9eab4d có 32 failures; hai số khác oracle, không được dùng để phóng đại mức giảm vulnerability. Findings và từng fix nằm ở `security/findings.md`.
2. Sáu lớp: identity/RBAC, input/retrieval validation, prompt boundary, NeMo/gateway runtime guards, deterministic action approval/budgets, audit/monitoring/red-team. Egress network enforcement trên kind chưa được chứng minh.
3. Threat model có 12 threats. Các rủi ro trọng tâm gồm prompt injection, poisoned contexts, PII/canary leak, excessive agency, stolen/spoofed key, bill shock, outage bypass và malicious coding patch; mỗi dòng có mitigation/test/owner/residual risk.
4. Có ba workload keys và hai service keys. Caps hiện tại app 1.25 + bot 0.50 + coding 1.00 + guard 1.00 + evaluator 0.75 = 4.50 USD. Đã chuyển 0.25 USD reserve từ app sang evaluator cho replays; tổng cap/envelope không tăng, xem `budget-reallocation.json`; envelope 5 USD, dừng admission ở 4 USD, TTL 7 ngày. Native cap là soft; concurrency overshoot được đo riêng.
5. Dashboard có 15 panels về spend, USD/hour, workload/model/tokens, budget, policy denials, failures, latency và reconciliation. Số chốt nằm trong cost report; không lấy ảnh đang scan làm tổng cuối.
6. NeMo dùng regex input/output + model self-check. NFKC và bỏ Unicode format characters hạn chế obfuscation. Chính sách chặn private PII/canary, instruction override và unauthorized actions; giữ câu hỏi kỹ thuật/giáo dục hợp lệ. Lỗi classifier được phân biệt với policy block và trả 503.
7. Poisoned-doc baseline trả raw malicious text qua `contexts` dù answer có thể từ chối. Fix kiểm từng chunk trước generation/serialization, thêm input/output guards và full-response oracle. UI evidence đối chiếu exact document/chunk/hash, không chỉ chụp refusal.
8. Không dùng Anthropic. ZenLayer native prompt cache được đo trên cùng workload: ba warm calls có 1792 cached tokens, bốn answers đúng; per-call estimate giảm từ 0.0007432 xuống 0.0002056 USD, khoảng 72.3%. Đây không phải mức tiết kiệm của toàn pipeline RAG.
9. Generation/classifier/judge đều cố định `gpt-4.1-mini`; embeddings là `text-embedding-3-large` với 1024 dimensions. Chưa adaptive routing hoặc fallback, vì chưa có quality/cost/isolation evaluation để bật các optional feature này.

## Số đo kết thúc

- Ledger known cost: **1.23455561 USD**. Gồm các attempts/iterations, guards/judges/embeddings và UI. Catalog estimate, chưa có invoice. Có **148 admission IDs chưa có completion**, được giữ và ghi unknown trong [Cost_Report](../evidence/day6/Cost_Report.md), không tự gán phí bằng 0.
- Concurrency 2: **40/40** expected answers. Enforced p95 **12.494s**, paired-overhead p95 **10.804s**. Candidate targets: chat <=15s MET, overhead <=3s NOT MET; giữ nguyên ngưỡng sau đo.
- Baseline/final/verifier cùng source và dataset; raw failed/incomplete reports giữ riêng trong [evidence index](../evidence/day6/README.md).
- Handoff replicas và corpus được ghi thực tế trong `handoff.json`; không tạo AWS resources.

## Giới hạn đối soát và handoff

- Verifier trả `PASS`, `runtime_verified=true`, nhưng scope của công cụ là `partial-runtime-contract` và `milestone_complete=false` theo thiết kế. Kết luận Must-have dựa thêm vào bảng MH, Edge, Slack/coding, fault và FinOps evidence, không sửa output verifier.
- Native evaluator thiếu một completion lịch sử trị giá 0.0004324 USD; ledger/dashboard vẫn tính đầy đủ. Nguyên nhân chưa xác định, không sửa counters. Xem [đối soát](../evidence/day6/Cost_Report.md).
- Handoff ngày 01/10: app/worker/web/gateway/guard/Grafana Ready 1, baseline 0, queue 0, chỉ còn guide chuẩn. Local node từng NotReady và các container restart lúc 06:26 UTC; readiness/accounting đã phục hồi, tunnel Grafana được reconnect. Acceptance đã hoàn tất trước sự kiện này; không nhận production HA.
- Alert `Day6KeyBudgetNearLimit` vẫn firing cho evaluator: spend 0.7045703/0.75 USD, reserve khoảng 0.04543 USD. Không tăng cap để dập alert.
