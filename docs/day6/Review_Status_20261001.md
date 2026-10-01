# Day06 - Rà soát đầu ngày 01/10/2026 (lịch sử)

> Báo cáo lịch sử trước khi gia hạn key và hoàn tất replay. Kết quả cuối đã cập nhật tại [Self_Check](Self_Check.md); nội dung dưới giữ nguyên để theo dõi các gap đã xử lý.

**Kết luận tại thời điểm rà soát: chưa hoàn thiện để nghiệm thu toàn bộ Day06.** Phần triển khai chính đã có, nhưng nghiệm thu source mới nhất, FinOps và đóng gói bàn giao còn thiếu.

## Source và kiểm tra mới

- Branch local: `day6-security-finops`, HEAD `3db6ead`.
- Source fingerprint: `5161df8e329e3dfdeef4e0eca3d225b6f39814403eb52cf9da224000b4e09f20`, khớp snapshot frozen cuối.
- Chạy lại `make test-day6 PYTHON=tmp/day6/venv/bin/python`: **57 passed**, Ruff check/format PASS. Có 14 deprecation warnings từ dependency NeMo; không phải test failures.
- Bộ này loại trừ live acceptance, vì vậy 57 tests không thay cho final scan/verifier.
- Local main và cached origin/main vẫn ở `c3f0442` (Day05). Nhánh Day06 chưa có upstream; không fetch remote trong lượt rà soát này.
- Docs/evidence Day06 vẫn có modified/untracked files, chưa được commit bàn giao.

## Đối chiếu yêu cầu

| Nhóm | Trạng thái có bằng chứng | Phần còn thiếu |
|---|---|---|
| MH1-4: Promptfoo, coverage, initial, fixes | Config pin 0.123.1; dataset 164 cases; initial và các fix commits có | Không dùng các scan lịch sử thay nghiệm thu source hiện tại |
| MH5: final no HIGH/CRITICAL | Bản source 101094a từng final 164/164 PASS | Source 3db6ead chưa có final/eval.json và verifier/result.json |
| MH6-9: guardrails, gateway, 3 keys, app routing | Source đã triển khai; runtime evidence guard/auth/budget/app/bot/coding có từ 29/09 | Chốt lại full acceptance trên source mới nhất |
| MH10: Grafana cost | Có dashboard 15 panels và alert firing/resolved lịch sử | Grafana hiện 0/0; thiếu final reconciliation, Cost_Report và ảnh chốt |
| MH11: AWS budget | N/A vì lượt triển khai không dùng AWS | Không cần bổ sung AWS chỉ để hoàn thành Day06 local |
| MH12: threat model | Có 12 threats với mitigation/test/owner/residual risk | Không có blocker tài liệu đã xác định |

## Lượt test cuối và runtime hiện tại

- `baseline-single-choice/start.json` bắt đầu 29/09/2026 14:47 UTC, đúng source 3db6ead. Chỉ có 112/164 result records; chưa có eval tổng kết.
- Không thấy tiến trình acceptance_chain, run_acceptance, Day06 scan/verifier hoặc Promptfoo eval còn chạy ở thời điểm rà soát. Không ghi trạng thái này là đang chạy.
- `final-before-capability-fix/` có 164/164 PASS nhưng source khác. Verifier tương ứng ở `verifier-oracle-inconsistent-incomplete/` là **INCOMPLETE**; verifier cũ hơn ở `verifier-budget-race-failed/` là **FAIL**.
- Kubernetes local: API 1/1, ingestion-worker 1/1, gateway 1/1, guardrails 1/1, baseline 1/1. Grafana 0/0. Đây là readiness hiện tại, không phải bằng chứng model E2E mới.
- Chưa có `final/eval.json`, `verifier/result.json`, `runtime/cost-reconciliation.json`, `grafana-prometheus-reconciliation.json`, `latency-concurrency 2.json`, `Cost_Report.md` trong evidence hiện tại.

## E2E, optional và bàn giao

- Edge upload/chat/citation, poisoned retrieval, policy/budget/outage recovery và Slack flows đã có ảnh/evidence lịch sử. Chưa chốt toàn bộ E2E cho source cuối.
- UI-08 mở local HTML report còn BLOCKED bởi browser URL policy. Quyền upload file URL đã hoạt động; hai việc này khác nhau.
- Provider prompt caching và PII checks đã có evidence. Semantic cache, adaptive routing và fallback vẫn disabled/chưa triển khai theo optional gates.
- PR/nightly workflow có trong `.github/workflows/security.yml`; chưa có remote/live CI PASS và chưa provision model credentials cho GitHub.
- Publish Day06 trước đó bị automatic approval review từ chối vì chưa có quyền publish branch lên public remote trong scope Day06; quyền merge/push Day05 không được coi là quyền Day06. Chưa retry publish trong lượt rà soát này.

## Thứ tự hoàn tất

1. Giữ nguyên raw interrupted run, kiểm corpus/keys/readiness/budget, rồi chạy mới baseline-final-verifier trên cùng source. Không nối thêm rows để biến báo cáo bị gián đoạn thành complete.
2. Đo latency concurrency 2, đối soát ledger/native spend/Prometheus và viết Cost_Report; báo trung thực target nào không đạt.
3. Restore Grafana, scale baseline về 0 sau đo; hoàn tất ảnh dashboard và Edge smoke cho capability boundary mới.
4. Cập nhật self-check từ kết quả thực, rà secrets, commit docs/evidence. Publish/remote CI chỉ thực hiện khi quyền Day06 đã rõ.

Lượt rà soát này chỉ chạy offline tests và đọc trạng thái runtime; không tạo AWS resources, không chạy paid model replay, không đổi replicas/caps hay publish remote.
