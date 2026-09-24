# Day 04 - Bộ prompt Observability, AIOps và RCA

**Rà soát:** 24/09/2026. **Nguồn chuẩn:** [Specification v3.3, mục 0, 4.4 và 8](../Running-Project-Specification-Student.md).

Bộ prompt tiếng Việt này dành cho InsightHub kế thừa Day 01-03, mục tiêu rubric L3. Mỗi prompt có bốn phần: mục tiêu, ràng buộc, tiêu chí/đầu ra và ví dụ. Đây là phiên bản chuẩn hóa để sử dụng tiếp, không phải bản chép nguyên văn các lượt chạy trước. Ba mục nhật ký cũ được giữ riêng tại [day4.md](day4.md).

Đọc [review hiện tại](../docs/day4/Review_and_Self_Check.md) trước khi chạy. Quiz do trainer phụ trách, không thuộc phạm vi triển khai. Không triển khai Should-have/Nice-to-have hoặc tính năng Day 05-06.

## D4-P01 - Đối chiếu yêu cầu và lập kế hoạch

**Đầu vào:** specification; `AGENTS.md`; source/evidence Day 01-03; kế hoạch Day 04; verification contract.

```text
MỤC TIÊU
Đóng vai kỹ sư SRE phụ trách InsightHub. Đối chiếu mục 0, 4 và 8 của
Running-Project-Specification-Student.md với source và evidence hiện có.
Lập kế hoạch đạt Must-have và acceptance Day 04 trong phạm vi L3.

RÀNG BUỘC
Chỉ khảo sát ở bước này. Giữ contract upload/chat, async worker, database
schema, embedding identity và năm thành phần Day 01-03. Tái sử dụng local
Kind, namespace insighthub-dev và monitoring; ghi rõ khác biệt so với
namespace ví dụ. Quiz không thuộc phần triển khai. Không thêm ChatOps,
auto-remediation, Sift/SLO mở rộng, MLflow, training, Promptfoo hoặc LiteLLM.
Không push remote. Tôn trọng quyền và phạm vi đã duyệt trong phiên, không
xin lại cùng thao tác. Đầu vào còn thiếu phải ghi rõ, không tự suy diễn.

TIÊU CHÍ VÀ ĐẦU RA
Lập bảng: requirement ID, file hiện có, trạng thái, phần thiếu, evidence
cần thu và cách kiểm chứng. Bao phủ MH1-MH10, MH12, NFR, prompt log;
ghi MH11 loại khỏi phạm vi theo trainer. Phân biệt source đã có, static
tests đạt và runtime đã quan sát. Lập thứ tự telemetry -> rules/dashboard
-> baseline -> ba incident tuần tự và recovery -> RCA -> review/bàn giao.

VÍ DỤ
MH3: JSON đủ 9 query panels mới chứng minh cấu hình; cần ảnh dashboard
trong khoảng workload, đủ chín nội dung và không có No data/query error.
Có token/RBAC chưa chứng minh coding host đã gọi MCP thành công.
```

**Lý do thiết kế:** Mỗi kết luận phải truy về yêu cầu và bằng chứng; verifier PASS không thay toàn bộ nghiệm thu.

## D4-P02 - Telemetry, dashboard và Slack

**Đầu vào:** kế hoạch đã duyệt; metrics ứng dụng; Helm chart; `observability/`; cấu hình MCP Day 02-04.

```text
MỤC TIÊU
Triển khai hoặc rà soát telemetry cho đủ web, api, ingestion-worker,
PostgreSQL và Redis; dashboard RED/USE; Alertmanager tới Slack #alerts.

RÀNG BUỘC
Monitoring opt-in, không đổi contract ứng dụng. Labels hữu hạn; không
đưa document_id, user_id, prompt, raw URL hoặc secret vào metrics.
API/worker dùng metrics sẵn có; PostgreSQL/Redis dùng exporter; web dùng
kube-state-metrics/kubelet cho health/resources. Queue ARQ là sorted set,
đo outstanding entries đúng queue key. Không biến mất scrape/Redis down
thành queue khỏe với giá trị 0. Usage generation phải do provider trả về,
giá đúng model đã duyệt. Cost không bao gồm embedding/hạ tầng và không
phải hóa đơn. Webhook/API key chỉ ở runtime, không xuất vào log/evidence.

TIÊU CHÍ VÀ ĐẦU RA
ServiceMonitor discover đúng named ports/labels/namespace; targets dự kiến
UP, có dữ liệu đủ năm thành phần, giữ HTTP route labels chính xác.
Một dashboard đúng 9 query panels cho solution này: rate, errors, duration,
queue depth, token usage, LLM p95, estimated generation cost, pod resources,
deployment history kèm annotation rollout thật. Retention 15d, resource
requests/limits; expensive queries có recording rules. Helm lint/render,
tests và runtime checks có kết quả. Lưu ảnh dashboard, timestamp/permalink
Slack thật khi test đã được phép; không coi config là delivered.

VÍ DỤ
Redis khỏe, queue key không tồn tại: queue=0 có thể hợp lệ.
redis_up=0 hoặc mất scrape: unknown/unavailable, không suy ra queue=0.
Lượt lab đã duyệt dùng giá input 5/output 30 USD mỗi triệu token cho
gpt-5.6-sol; ghi nguồn/ngày giá, không coi giá này là bất biến.
```

**Lý do thiết kế:** Làm rõ semantics của queue, coverage và giới hạn cost thay vì chỉ đếm targets/panels.

## D4-P03 - Anomaly rules và baseline

**Đầu vào:** canonical rules; promtool tests; provider/model, budget, quota request đã duyệt.

```text
MỤC TIÊU
Hoàn thiện detector cho LLM p95, queue backlog và HTTP server-error ratio.
Xác minh baseline đủ điều kiện trước khi đánh giá incident.

RÀNG BUỘC
Dùng observability/chart/files/anomaly-rules.yaml làm canonical source.
Cấu hình lab: baseline 1h, offset 10m, recording interval 1m, for 2m;
dự trù 75 phút thu baseline. Không hạ xuống 5-10 phút, bịa/backfill evidence
hoặc đổi threshold sau incident chỉ để PASS. Giữ impact/volume guards.
Phân biệt NaN, missing, stale với 0; guard phải chứng minh đủ mẫu hợp lệ,
không chỉ đếm timestamp có NaN. Workload có giới hạn request, thời gian
và ngân sách. Giữ quota đã duyệt; thiếu quota thì báo, không tự gọi thêm.

TIÊU CHÍ VÀ ĐẦU RA
Promtool check/test đúng file; kiểm normal, pending/firing, recovery,
no traffic, missing series, Redis down và NaN histogram windows.
Chứng minh rules loaded/healthy; baseline continuity, finite values,
usage thật và estimated cost trong budget. Lưu start/end UTC, sample
counts, query/time range. Hồ sơ lịch sử phải giữ thời điểm gốc, không
gọi việc đọc lại hồ sơ là một lần baseline/live verification mới.

VÍ DỤ
60 timestamp với p95=NaN không phải 60 mẫu latency hợp lệ.
29254 input và 17901 output ở mức giá 5/30 USD mỗi triệu token tương ứng
0.68330 USD generation, chưa tính embedding/hạ tầng.
```

**Lý do thiết kế:** Tách thời lượng baseline khỏi chất lượng mẫu; kiểm cả lỗi biên tests cũ chưa bao phủ.

## D4-P04 - Ba incident, recovery và AI RCA

**Đầu vào:** baseline hợp lệ; `scripts/chaos/`; context/namespace và quota được phép; [prompt RCA](../prompts/rca-template.md).

```text
MỤC TIÊU
Chạy tuần tự LLM latency spike, queue backlog và error burst trong lab
được phép. Mỗi incident có alert thật, Slack, recovery và RCA riêng.

RÀNG BUỘC
Executor/operator thực hiện mutation bằng fault scripts đã review.
AI RCA điều tra qua Prometheus MCP và Kubernetes MCP read-only.
Xác minh context/namespace, lưu trạng thái trước lỗi và cách restore.
Chỉ chuyển incident khi lỗi trước đã khôi phục. Không vượt quota/budget.
Không tạo RCA giả. Curl/kubectl không thay actual host MCP calls;
thiếu tool thì ghi gate MCP chưa đạt, không tự đổi loại bằng chứng.

TIÊU CHÍ VÀ ĐẦU RA
Ghi start, pending, firing quan sát được, Slack FIRING, recovery bắt đầu,
resolved và Slack RESOLVED. Latency phải fire trong 5 phút từ inject.
Latency: restore proxy, chat thành công. Backlog: restore replicas,
queue drain, documents ready. Error: restore proxy, chat thành công.
Dùng prompts/rca-template.md cho từng incident. Lưu ba JSON distinct tại
docs/evidence/day4, không dùng một báo cáo tổng thay ba RCA. Mỗi báo cáo
có metric, labels, timestamp RFC3339, finite value trong incident window,
phép kiểm bác bỏ, giới hạn suy luận và references tới MCP evidence.
Kết thúc không còn fault/load generator; báo trạng thái thực và cost.

VÍ DỤ
Queue tăng và worker replicas=0 mới là tương quan ban đầu. Kết hợp
thời điểm scale, API nhận tài liệu, queue giảm/documents ready sau restore
mới củng cố giả thuyết thiếu ingestion capacity.
```

**Lý do thiết kế:** Tách quyền gây lỗi khỏi điều tra và yêu cầu đủ ba chu trình có provenance.

## D4-P05 - MLOps overview và self-check

**Đầu vào:** specification mục 8.3/8.9; `mlops-overview-notes.md`; kiến trúc InsightHub.

```text
MỤC TIÊU
Review notes theo bốn block Day 04: app/model artifact; lifecycle và
ownership; bốn khái niệm core; tình huống quyết định release.

RÀNG BUỘC
Chỉ kiến thức kiến trúc, không dựng ML platform, registry server,
training/retraining hoặc model serving mới. Không làm quiz thay học viên.
Phân biệt DevOps vận hành workflow đã duyệt với tự quyết retrain/promote.
Data drift không tự chứng minh concept drift hoặc chất lượng đã giảm.

TIÊU CHÍ VÀ ĐẦU RA
So sánh app/model qua artifact, version/lineage, quality gate, compatibility.
Mô tả Data -> Train -> Validate -> Registry -> Deploy -> Monitor -> Retrain
Decision; nêu DevOps/ML/Data/Product owner. Giải thích Registry, Approval
Gate, Drift, Rollback; rollback kiểm model, preprocessing/features, schema
và runtime. Trả lời self-check về drift, khi nào báo ML và giới hạn ownership.

VÍ DỤ
Model tăng điểm tổng nhưng giảm chất lượng tiếng Việt hoặc vượt latency
gate: chưa promote. DevOps lưu version/evidence và chuyển owner review;
không tự nới gate hoặc tự quyết retrain.
```

**Lý do thiết kế:** Đủ learning outcomes mà không biến overview thành dự án MLOps ngoài phạm vi.

## D4-P06 - Review độc lập và bàn giao

**Đầu vào:** diff; Day 04 artifacts; logs; evidence manifest và verifier report.

```text
MỤC TIÊU
Đóng vai reviewer Day 04. Đối chiếu source, prompts và evidence với từng
Must-have/NFR; kết luận có đủ nghiệm thu hay còn thiếu căn cứ.

RÀNG BUỘC
Verifier PASS không đồng nghĩa milestone hoàn tất: đọc scope/checks và
specification_review_required. Không sửa verifier/assertions để PASS.
Không ghi mẫu mới thành prompt đã dùng; không đoán host version/model/auth.
Model coding host khác model runtime RAG. Không gọi API trả phí chỉ để
review tài liệu. Quiz ngoài phạm vi; không push hoặc tự tạo PR.

TIÊU CHÍ VÀ ĐẦU RA
Kiểm >=3 prompt log, metadata có căn cứ, cấu trúc bốn phần, lý do hiệu quả
và quyết định review. Mẫu chưa chạy phải được ghi rõ. Kiểm source/artifact
hashes, ba incident distinct, finite citations đúng window, Slack links,
host MCP calls, ảnh 9 panels có dữ liệu, baseline >=1h và recovery.
Kiểm MLOps bốn block, cost đúng phạm vi. Chạy kiểm tra phù hợp thay đổi;
quét secret, em dash và git diff --check. Cập nhật Review_and_Self_Check,
Runtime_Validation và PR_Description đúng bằng chứng, kèm finding/tác động/
cách đóng. Chỉ kết luận hoàn tất khi mọi gate trong phạm vi có evidence.
Commit local khi đã được phép, tuyệt đối chưa push.

VÍ DỤ
status=PASS, scope=partial-runtime-contract, milestone_complete=false
chỉ chứng minh checks liệt kê; không tự chứng minh dashboard không No data,
MCP đã gọi hoặc causal reasoning của RCA đúng.
```

**Lý do thiết kế:** Ngăn kết luận quá mức, giữ evidence tái kiểm được và tuân thủ phạm vi bàn giao.

## Ghi log sau khi sử dụng

Ghi prompt ID/phiên bản, nội dung thực đã gửi, thời gian có múi giờ,
host/version/model/auth mode đã xác nhận, input files, kết quả/tool-call
references, lý do hiệu quả và quyết định review. Metadata không lưu thì
đánh dấu “chưa xác minh”, không lấy model Zenlayer điền cho coding host.
