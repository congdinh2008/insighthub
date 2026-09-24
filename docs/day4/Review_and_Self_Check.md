# Day 04 - Rà soát yêu cầu và tự kiểm tra

**Ngày review:** 24/09/2026. **Branch:** `day4-observability`. Quiz đã được trainer loại khỏi phạm vi.

**Kết luận:** Luồng lab Day 04 đã chạy thật: baseline 75 phút, ba incident phục hồi, Slack FIRING/RESOLVED và ba RCA có tám mẫu Prometheus đối chiếu live. Hai lỗi biên của rules đã sửa và kiểm thử. Ngày 24/09, hệ thống local được kiểm lại với 22/22 targets UP; Grafana đã render đủ chín panel và có ảnh nghiệm thu trong khung incident. Verifier PASS nhưng ghi `scope=partial-runtime-contract` và `milestone_complete=false`; vì vậy chưa dùng nó để tuyên bố hoàn tất toàn bộ milestone. Lời gọi MCP đúng thời điểm incident gốc vẫn chưa xác minh. Theo chỉ đạo trainer, Day 04 bàn giao danh sách prompt chuyên nghiệp thay cho nhật ký prompt.

## Ma trận nghiệm thu

| Yêu cầu | Kết quả | Căn cứ |
|---|---|---|
| MH1/MH2 - ServiceMonitor và năm thành phần | Đạt trong local lab; 22/22 targets UP, API/worker/PostgreSQL/Redis cùng Kubernetes web/resources | [Runtime](../evidence/day4/Runtime_Validation.md) |
| MH3 - Dashboard chín panel | Đạt local: 9/9 biểu đồ đã render dữ liệu, không có "No data", annotation hiện diện trong khung incident | [Ảnh](../evidence/day4/grafana-day4-9-panels.png), [panel validation](../evidence/day4/dashboard-panel-validation.json) |
| MH4/MH5 - Recording và anomaly rules | 20 rules, ba alerts; promtool và edge-case tests PASS | [Rules](../../observability/chart/files/anomaly-rules.yaml), [tests](../../observability/tests/day4-edge-cases.test.yaml) |
| MH6 - Slack | Test alert và ba cặp FIRING/RESOLVED có permalink | [Runtime](../evidence/day4/Runtime_Validation.md) |
| MH7-MH10 - Incident, RCA, citation | Ba incident distinct, recovery, tám mẫu finite có labels/timestamp/value; live verifier PASS | [Manifest](../evidence/day4/day4.json), [MCP investigation](../evidence/day4/mcp-investigation.json) |
| MH11 - Quiz | Ngoài phạm vi theo chỉ đạo trainer | Không thực hiện |
| MLOps notes | Đủ bốn block overview, không triển khai ML platform | [Notes](../../mlops-overview-notes.md) |
| Baseline và chi phí | 4.505 giây, 70/70 chat; generation estimate cuối `$0.68330` so với budget `$5` | [Baseline](../evidence/day4/baseline.json), [Runtime](../evidence/day4/Runtime_Validation.md) |
| Danh sách prompt Day 04 | Bảy prompt tiếng Việt có mục tiêu, ràng buộc, đầu ra và ví dụ; trainer không yêu cầu nhật ký prompt trong lượt này | [Danh sách prompt](../../ai-prompts/day4.md), [RCA template](../../prompts/rca-template.md) |

## Findings và giới hạn

- **F01 đã sửa:** Queue không còn trả `0` khi Redis down hoặc mất scrape. Chỉ cho fallback `0` khi Redis `up=1`; có test Redis down, empty queue, backlog và missing scrape. Đây là sửa sau incident ngày 23/09, không gán ngược rule mới cho thời điểm incident.
- **F02 đã sửa:** Guard latency chỉ đếm mẫu p95 hữu hạn. Test một giờ NaN không qua guard. Band và ngưỡng một giờ giữ nguyên.
- **F03 đã điều tra bổ sung:** Ngày 24/09, client MCP thật gọi Prometheus `range_query` tám lần trên historical incident windows và Kubernetes `pods_list_in_namespace` read-only; tám giá trị trùng RCA. Dấu vết này chứng minh bước điều tra sau incident, không chứng minh coding host đã gọi MCP ngay trong incident ngày 23/09. Kubernetes snapshot lịch sử vẫn là bằng chứng riêng của lab.
- **F04 đã đóng:** Grafana UID `insighthub-day4` đã render chín biểu đồ có dữ liệu thật và annotation trong khung 15:40-16:05 UTC; ảnh 1600 x 1500 px đã được kiểm trực quan. Lượt chụp đầu cho thấy "No data" vì plugin Prometheus chưa đăng ký và đã bỏ ảnh đó. Tắt auto-update plugin bundled trên image read-only, nâng giới hạn Grafana local lên 1 CPU/1 GiB, xác nhận datasource health `OK`, rồi chụp lại ảnh hợp lệ.
- **Quyết định phạm vi của trainer:** Specification gốc có quy ước nhật ký prompt ở mục 4.4, nhưng lượt triển khai Day 04 này chỉ yêu cầu danh sách prompt chuyên nghiệp. `ai-prompts/day4.md` là prompt pack, không được trình bày như nhật ký hoặc bằng chứng prompt đã chạy.

## Kiểm tra sau sửa

- `make rules-day4`: 20 rules hợp lệ, cả hai promtool suites PASS.
- Pytest Day 04: 5/5 PASS; Helm lint/render PASS.
- Verifier Prometheus live: `PASS`, source digest khớp manifest mới, phạm vi `partial-runtime-contract`.
- Ba RCA giữ nguyên nội dung và hash lịch sử; không chạy lại baseline hay gọi provider trả phí.
- Helm observability local revision 9 giữ MCP ServiceAccount read-only; list pods được, đọc Secrets bị từ chối.
- kube-prometheus-stack local revision 6; Grafana 3/3 Ready, datasource Prometheus health `OK`, 22/22 targets UP, Day 04 alerts không còn firing.

## AIOps và MLOps self-check

RED theo request, USE theo resources/saturation/errors. Một giờ baseline là mức tối thiểu cho lab, không thay thế dữ liệu seasonal production. Band 3-sigma không bảo đảm tỷ lệ false positive cố định. RCA tách observed, inferred, unknown và buộc citation metric/labels/time/value; confidence không thay causal review. Queue depth đối chiếu worker replicas và document completion. MLOps notes phân biệt artifact, lifecycle/ownership, Registry/Approval Gate/Drift/Rollback và release case; không tự quyết retrain/promote.
