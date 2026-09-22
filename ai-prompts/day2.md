# Day 02 - Bộ prompt thực hiện solution

Năm prompt dưới đây dành cho học viên thực hiện bài MCP Protocol Integration từ solution Day 01. Đây là prompt pack được đề xuất, chưa phải log các phiên thực hành đã chạy. Đọc [specification mục 6](../Running-Project-Specification-Student.md) và [plan Day 02](../docs/plans/Day02_Implementation_Plan_v1.0.md) trước khi sử dụng.

| Prompt | Đầu vào | Đầu ra học viên cần review |
|---|---|---|
| D2-P01 | Source Day 01, specification và context | Architecture map, gap analysis, phạm vi Day 02 |
| D2-P02 | Gap analysis | Plan, lựa chọn backend/pin, quyền, test matrix và commit strategy |
| D2-P03 | Plan đã duyệt | Bốn backend MCP, lab, config, RBAC và tests đi cùng |
| D2-P04 | Diff/config và lab hoạt động | Findings, negative tests, host traces và regression |
| D2-P05 | Integration đã qua review | Debug case, Inspector/browser E2E, evidence và bộ bài nộp |

Mỗi prompt theo cấu trúc Ràng buộc -> Mục tiêu -> Tiêu chí chấp nhận -> Tham chiếu. Năm bước tạo năm nhóm đầu ra khác nhau; chỉ thêm prompt khi có vấn đề kỹ thuật cần xử lý, không tách một thao tác nhỏ thành một prompt riêng để tăng số lượng.

## D2-P01 - Phân tích kiến trúc và yêu cầu tích hợp

```text
RÀNG BUỘC
Đọc AGENTS.md và specification của checkout hiện tại trước.
Chỉ phân tích Day 02, chưa sửa ứng dụng, cài tooling hay tạo cluster.
Giữ solution Day 01: năm service mặc định, async ingestion, retry,
DB schema và API/UI contracts. Dùng một coding host là Codex.

MỤC TIÊU
Phân tích kiến trúc tích lũy Day 01 và khoảng trống Day 02.
Xác định Host/Client/Server, bốn backend Filesystem/Docker/K8s/
Prometheus và dữ liệu/quyền mà mỗi backend cần.
Giải thích Tools/Resources/Prompts và lựa chọn stdio/Streamable HTTP
dựa trên capabilities thật, không tự thêm tính năng vào server.

TIÊU CHÍ CHẤP NHẬN
Map đủ mười Must-have tới artifact và bằng chứng cần thu.
Phân biệt MCP mẫu với bốn tích hợp thật, SDK với host calls,
CLI baseline với MCP debug, fixture với live backend.
Chỉ ra metrics có thể tái sử dụng và lab prerequisites còn thiếu.
Đề xuất cập nhật context sáu section, tối đa 200 dòng.
Dẫn file nguồn cho kết luận; đánh dấu điều chưa kiểm chứng.

THAM CHIẾU
Running-Project-Specification-Student.md mục 0, 4, 6;
AGENTS.md; docker-compose.yml; tools/mcp/;
api/app/core/metrics.py; ingestion-worker/worker.py;
docs/Guide_Coding_Host_DO2603.md; scripts/VERIFICATION_CONTRACT.md.
```

**Vì sao cần:** Chốt đúng đầu vào tích lũy và acceptance trước khi chọn package hoặc mở rộng quyền.

**Học viên review:** Bốn backend là bốn tích hợp độc lập; một gateway hoặc bốn tools trên server mẫu không đủ. Cluster/Prometheus Day 02 chỉ phục vụ lab MCP, chưa là deployment Day 03 hoặc observability Day 04.

## D2-P02 - Lập plan và review thiết kế

```text
RÀNG BUỘC
Chưa triển khai. Chỉ dùng nguồn upstream chính thức của từng tool
để kiểm tra release/tag, config và quyền; không dùng latest.
Chọn bốn backend bắt buộc, ưu tiên MCP upstream chính chủ, có hoạt động
maintain và nguồn pin kiểm chứng được. Đánh giá độ phổ biến bằng dữ liệu,
không coi số sao là bảo đảm chất lượng. Tái sử dụng MCP InsightHub
hiện có làm server thứ năm cho health/document metadata. Không thêm AWS,
Terraform MCP, server trùng chức năng hoặc tính năng của day sau.

MỤC TIÊU
Lập plan trên branch dự kiến day2-mcp từ main đã hoàn thiện Day 01.
Tự review thiết kế theo requirement, compatibility, quyền truy cập,
khả năng tái lập và cách thu evidence qua Codex/Inspector.

TIÊU CHÍ CHẤP NHẬN
Có mapping MH1-MH10, Should-have được chọn và optional ngoài scope.
Chốt backend/version ứng viên, cách pin digest/checksum/dependencies,
host config, context/namespace, SA/ClusterRole/RoleBinding.
Filesystem chỉ project; K8s dùng SA read-only, không admin kubeconfig.
Đánh giá Roots, Docker socket, output nhạy cảm và Prometheus admin tools.
Có bước làm, file scope, expected result, positive/negative tests,
debug incident, Computer Use E2E, quiz và commit strategy.
Phân biệt quiz answer key với bằng chứng điểm quiz thực tế.
Dừng để tôi review toàn bộ plan trước implementation.

THAM CHIẾU
Kết quả D2-P01; specification mục 6.3-6.9;
docs/plans/Day02_Implementation_Plan_v1.0.md;
docs/MCP_Tool_Selection_DO2603.md và upstream đúng version.
```

**Vì sao cần:** Quyền và bằng chứng phải được thiết kế cùng integration, tránh bổ sung sau khi đã expose backend cho host.

**Học viên review:** Pin có nguồn thật, namespace được RBAC giới hạn; allowlist và read-only có enforcement; các giới hạn chưa đo không được coi là bảo đảm. Không dùng quiz mẫu để tự ghi đạt MH10.

## D2-P03 - Triển khai lab và bốn MCP backend

```text
RÀNG BUỘC
Chỉ thực hiện plan đã được tôi duyệt trên day2-mcp.
Giữ source/contracts Day 01, MCP mẫu và verifier hiện có.
Không ghi đè cấu hình host cá nhân, không commit runtime secrets.
Fault injection và teardown chỉ dùng project/cluster lab đã chọn.

MỤC TIÊU
Ghi baseline rồi dựng lab local và tích hợp bốn backend MCP.
Pin artifacts/locks, sinh config project Codex, Claude Code và Antigravity IDE
kèm template portable; chọn một host để nghiệm thu. Tạo SA mcp-readonly
và kiểm chứng kết nối bằng SDK trước khi nạp vào host.

TIÊU CHÍ CHẤP NHẬN
Compose mặc định vẫn đúng năm service. Override có Prometheus và
debug profile; kind dùng workload mẫu và namespace insighthub.
Kubeconfig SA riêng, quyền get/list/watch có scope, token giữ local.
Filesystem dùng signed image qua Docker MCP Gateway, profile project,
snapshot mount read-only, network disabled và ba read tools. Docker operations
dùng Gateway chính chủ với catalog project, argv đọc cố định và proxy enforce
project scope; Prometheus toolset hẹp. Không dùng
socket mount :ro hoặc tool annotation làm bảo đảm quyền độc lập.
Bốn server có tools/list và call thật trên live backend; lưu version,
protocol, backend identity và output. Không nới quyền khi gặp Forbidden.
Tests đi cùng config/implementation; báo rõ phần chưa xác minh.

THAM CHIẾU
Plan đã duyệt; AGENTS.md; tools/mcp/day2/ nếu đã được tạo;
upstream đúng tag và schema tool thực quan sát từ từng server.
```

**Vì sao cần:** Tạo một integration có thể dựng lại từ config và locks, thay vì các thao tác cài đặt chỉ tồn tại trên máy người làm.

**Học viên review:** Không có hardcoded credential/path cá nhân; chọn đúng Docker context và kubeconfig SA; kiểm tra actual tool list trước khi bật trong Codex. Đọc policy output, không chỉ thấy process đang chạy.

## D2-P04 - Review, kiểm thử quyền và host integration

```text
RÀNG BUỘC
Review diff trước, chỉ sửa findings trong scope plan Day 02.
Không đổi assertions/verifier để đạt PASS; không dùng native shell
thay host MCP calls. Negative tests dùng canary không chứa dữ liệu riêng.

MỤC TIÊU
Kiểm tra config, compatibility, permission boundaries và regression.
Nạp bốn backend bắt buộc và MCP InsightHub vào Codex, gọi tool bằng model/host và lưu trace thật.

TIÊU CHÍ CHẤP NHẬN
Findings có severity, file/cấu hình, evidence và cách sửa cụ thể.
Filesystem: allowed root, outside/traversal, discovery allowlist và write denial.
K8s: đọc pods được; mutation, exec, secrets, namespace khác bị chặn
bằng chính kubeconfig SA. Docker direct mutation call bị từ chối.
Prometheus có sample thật, đối chiếu cùng timestamp; admin bị chặn.
Có host calls thật của từng server đã chọn, gồm tên tool, input/output,
timestamp và backend ID; giữ approval của host, không dùng bypass.
Chạy regression Day 01/MCP mẫu và Day 02 tests; phân biệt verifier
partial PASS với hoàn thành toàn bộ rubric. Không ghi PASS khi chưa chạy.

THAM CHIẾU
Final diff; test matrix trong plan; scripts/check-agent-setup.py;
scripts/verify-day-2.sh; scripts/VERIFICATION_CONTRACT.md;
tests/milestones/day2/ và config đã làm sạch.
```

**Vì sao cần:** Kiểm chứng quyền ở lớp thực thi và kết nối từ host, hai phần không được chứng minh bằng một file config hợp lệ.

**Học viên review:** Có denied response thực; canary không thay đổi; evidence không chứa secrets. Nếu lỗi do wrong context hoặc token hết hạn thì sửa cấu hình đúng, không cấp cluster-admin để tiếp tục.

## D2-P05 - Debug thực tế, browser E2E và bàn giao

```text
RÀNG BUỘC
Chỉ tạo incident đã định nghĩa trong profile lab Day 02.
Docker/K8s MCP giữ read-only; operator áp dụng remediation đã review.
Không tạo benchmark, screenshots, quiz score hoặc tool output giả.
Chỉ ghi nội dung phục vụ hoàn thiện và tái lập Day 02.

MỤC TIÊU
Thực hiện crashed-container RCA qua Docker MCP; dùng Computer Use
điều khiển Inspector/browser để nghiệm thu và hoàn thiện bài nộp.

TIÊU CHÍ CHẤP NHẬN
Case study có symptom, timeline, hypotheses, log/config evidence,
root cause, remediation, retest; đo CLI/MCP cùng incident, nêu giới hạn.
Inspector: từng server Connected, list tools, invoke thành công,
ít nhất một screenshot rõ output/server mỗi backend, không lộ token.
Chạy đủ B01-B08 trong plan bằng UI, lưu expected/actual và evidence.
Hoàn thiện runbook, self-check, quiz/answer key; điểm quiz lớp chỉ ghi
khi có bài làm và kết quả thật. Tổng hợp MH đạt/chưa đạt có link.
Chuẩn hóa Conventional Commits theo mục đích, viết PR description
[Day 2] Integrate MCP backends with read-only lab access.
Dừng lab đúng scope; trình final diff/evidence để review trước merge.

THAM CHIẾU
Plan Day 02; debug-session-day2.md; docs/day2/;
docs/evidence/day2/; specification mục 4 và 6.5-6.9.
```

**Vì sao cần:** Đưa integration vào một quy trình chẩn đoán thực tế và tạo solution học viên có thể tự thực hành, tự đối chiếu kết quả.

**Học viên review:** RCA dẫn evidence thay vì suy đoán; Inspector screenshots cùng config với host; mọi checkbox đạt có kết quả tương ứng; commit và PR mô tả trạng thái cuối.

## Ghi nhận sau khi học viên thực hành

Mỗi prompt được dùng cần có bản ghi ngắn theo quy ước mục 4.4 của specification:

- Host/product/version, model và auth mode thực dùng, không ghi token.
- Thời điểm, checkout/source revision, context/config đã làm sạch.
- Input, kết quả/evidence và lý do prompt có tác dụng trong bước đó.
- Quyết định review: đã chấp nhận hoặc điều chỉnh gì, liên kết diff/tests.

Prompt pack giữ nội dung hướng dẫn ổn định. Transcript/tool traces và kết quả thực hành nằm trong evidence Day 02.
