# Day06 - Cost và performance report

Snapshot: 2026-10-01T06:22:34.505022+00:00. Source `c49623b4b2600af16d9e01e01f0b2c1c95afc9e88e30eae03df712fc6593dd8d`. Currency USD, actual provider usage x ZenLayer catalog ngày 29/09/2026; chưa có invoice. Local-only, AWS N/A.

## Chi phí toàn lượt lab

Chi phí đã biết theo completion ledger: **1.23455561 USD**, tương đương 24.69% envelope 5 USD. Bao gồm generator, các baseline/iterations bị lỗi hoặc dừng, final/verifier, embeddings, guards/judges, coding attempts, cache và UI/runtime probes. Codex subscription không nằm trong số này.

| Identity | Ledger USD | Native DB USD | Delta USD | Cap USD | Cached input tokens |
|---|---:|---:|---:|---:|---:|
| insighthub | 0.14344371 | 0.14344371 | -1.17e-15 | 1.25 | 0 |
| chatops-bot | 0.00205440 | 0.00205440 | 0 | 0.50 | 0 |
| coding-workflow | 0.00393200 | 0.00393200 | 8.67e-19 | 1.00 | 5376 |
| guardrail | 0.38012280 | 0.38012280 | -2e-15 | 1.00 | 5760 |
| evaluator | 0.70500270 | 0.70457030 | 0.000432 | 0.75 | 0 |

Admission IDs: 10079; completion IDs: 9931; unresolved admitted: 148; duplicate completions: 0; completions thiếu cost: 0. LiteLLM có 530 failure callbacks, trong đó 148 IDs khớp admission. Callback có thể chạy khi request bị chặn trước provider, nên panel 'Upstream errors' không phải số lần API trả phí đã thất bại. Không suy unknown charge thành 0. Ledger/native agreement không thay đối soát invoice.

## Cùng frozen dataset, baseline và enforced

| Lượt | Executed / passed | Benign | Full-window USD | USD / semantic success | Blocked / released |
|---|---:|---:|---:|---:|---:|
| baseline-single-choice | 164 / 132 | 20/20 | 0.07892332 | 0.00059790 | 0 / 164 |
| final | 164 / 164 | 20/20 | 0.05856672 | 0.00035711 | 125 / 39 |
| verifier | 164 / 164 | 20/20 | 0.05800792 | 0.00035371 | 125 / 39 |
- baseline-single-choice: evaluator transport failures 2, recovered calls 2, unrecovered failures 0.
- final: evaluator transport failures 0, recovered calls 0, unrecovered failures 0.
- verifier: evaluator transport failures 0, recovered calls 0, unrecovered failures 0.

Full-window join dùng thời điểm start/end với các calls chạy tuần tự. Bao gồm guard, evaluator và ingestion trong khoảng đo. Cost per success dùng outcome oracle, khác cost per completed call của dashboard. `final/cost.json` là generation-only catalog upper estimate theo schema verifier, không phải tổng lab và không biểu diễn cached input discount. Không cộng hai bảng trên với nhau vì các cửa sổ là subset của tổng lab.

Final blocked responses có 0 paid target-generation completion cùng parent ID; verifier có 0. Classifier/judge vẫn tốn phí và đã được tính trong full-window ledger.

## Budget enforcement

Cả 3 keys có automatic budget-specific denial ở concurrency 1/2/5. Overshoot lớn nhất 0.00010820 USD; accounting window đo lớn nhất 8.41s. Tất cả caps đã restore. Đây là soft cap, không phải reservation/hard cut-off. Bound của chat probes dùng tối đa 4 UTF-8 bytes/code point cho 24000 characters và 1024 output tokens, single completion. Các số đo trước fix được giữ riêng, không rewrite.

`budget-alert.json` xác nhận threshold alert firing/resolved và cap được restore. Không claim gửi alert ra email/Slack ngoài rule evaluation.

## Prompt caching

Cùng prompt/model/temperature và bốn answers đúng: cold 1846 input/3 output, cached 0; warm 1846 input/3 output, cached 1792. Giá input 0.40, output 1.60, cached input 0.10 USD/1M tokens. Estimate/call giảm 0.0007432 -> 0.0002056 USD (72.3%). Latency warm không nhanh hơn trong mẫu này; không nhận cải thiện latency. Không bật proxy response cache hay semantic cache. Xem `prompt-cache.json` và hai ảnh pricing.

## Latency và giới hạn

- baseline-single-choice,20 benign serial: p50 2.148s, p95 3.411s.
- final,20 benign serial: p50 8.788s, p95 11.019s.
- verifier,20 benign serial: p50 9.144s, p95 12.943s.

Concurrency 2, 20 câu/profile: baseline p95 3.778s, enforced p95 12.494s, paired-delta p95 10.804s. Expected answers: baseline 20/20, enforced 20/20. Candidate chat target <=15s: MET; overhead target <=3s: NOT MET. Không thay ngưỡng sau phép đo để nhận PASS.

Paired delta gồm provider/network/run variance, không phải phép đo cô lập CPU hoặc riêng classifier. API và gateway kiểm nhiều lớp nên có overhead; Docker VM khoảng 4 GiB, Grafana tạm pause trong scan rồi restore. Nếu target chưa đạt thì đó là giới hạn performance còn mở, không làm giả thành security PASS.

Adaptive model routing, semantic cache và fallback chưa được bật/đánh giá; không claim mức giảm cost per success của các feature này hoặc rubric Level 4. Generation/classifier/judge cố định gpt-4.1-mini, embeddings text-embedding-3-large, 1024 dimensions.

## Native accounting exception đã đối soát

- Prometheus và completion ledger khớp chính xác ở snapshot cuối. Native totals của app/bot/coding/guard khớp trong sai số floating point.
- Evaluator native spend thấp hơn ledger **0.0004324 USD**. Join theo provider request ID xác định đúng một completion ngày 29/09/2026 16:22:29 UTC có 273 input/202 output tokens, provider ID `chatcmpl-ETUszXWBhEm7sPVSDUeW5qSgpAJJ7`, thiếu trong native SpendLogs. Chi phí của completion này vẫn được cộng đầy đủ trong ledger/dashboard.
- Tất cả chat rows join được đều khớp cost; aggregate embedding cost cũng khớp. Xem `native-request-reconciliation.json`. Không sửa native counters để làm delta bằng 0. Nguyên nhân mất native row lịch sử chưa được xác định; không quy thành lỗi pricing hay invoice.
- 148 admission IDs có failure callback nhưng không có completion/usage, gồm các lượt provider-expired và transport lỗi. Phần charge chưa chứng minh được giữ unknown; tổng trên không phải invoice cuối.
- Evaluator còn khoảng 0.0454 USD trong cap 0.75 USD, nên cần rà lại reserve trước một full replay mới. Tổng envelope 5 USD và global stop 4 USD giữ nguyên.
