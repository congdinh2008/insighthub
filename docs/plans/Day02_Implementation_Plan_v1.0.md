# Day 02 - Kế hoạch triển khai MCP Integration

**Trạng thái:** Đã duyệt triển khai; cập nhật lựa chọn MCP theo review nguồn chính chủ. **Lớp:** DO2603. **Ngày:** 17/09/2026.

Mục tiêu: xây solution Day 02 để học viên tái lập bốn tích hợp MCP, kiểm chứng quyền và thực hiện một ca debug có bằng chứng. Nguồn yêu cầu là [Specification v3.3, mục 0, 4 và 6](../../Running-Project-Specification-Student.md), [lab Day 02](../lab-guides/Day2-MCP-Protocol.md) và [host guide](../Guide_Coding_Host_DO2603.md).

Baseline: `main` tại `d6766099102944eedbf0d2c532f460b385917f3f`. [CI Day 01](https://github.com/congdinh2008/insighthub/actions/runs/35208957664) đã success. Branch triển khai: `day2-mcp`.

## 1. Phân tích hiện trạng và phạm vi

| Hạng mục | Hiện trạng đã đọc/kiểm tra | Công việc Day 02 |
|---|---|---|
| Application | Day 01 có web, API, PostgreSQL, Redis và ARQ worker; async upload, retry và chat đã kiểm thử | Giữ contract, source nghiệp vụ và năm service mặc định |
| MCP mẫu | `tools/mcp` có SDK, hai tool InsightHub và tool Prometheus tùy chọn | Giữ regression; không tính mẫu này thay bốn backend bắt buộc |
| Host | Codex CLI 0.154.0; helper hiện chỉ sinh config cho MCP mẫu | Sinh config project cho Codex, Claude Code và Antigravity IDE từ cùng năm backend; nghiệm thu runtime bằng Codex |
| Kubernetes | Có `kubectl`; không có context trong kết quả kiểm tra hiện tại; chưa có `kind` trên PATH | Cluster kind riêng, namespace `insighthub`, workload mẫu, ServiceAccount và RBAC |
| Prometheus | API/worker đã có metrics; chưa có cấu hình Prometheus Day 02 trong repo | Scrape metrics hiện có để luyện query MCP |
| Evidence | Chưa có debug case, Inspector hay host traces của bốn backend Day 02 | Thu mới, gắn source/config/version và thời điểm chạy |
| Context | AGENTS.md hiện giới hạn Day 01 | Cập nhật phần tích lũy Day 01-02, giữ sáu section và tối đa 200 dòng |

Phạm vi nghiệm thu: toàn bộ 10 Must-have; ba Should-have phù hợp local là namespace/context cố định, Kubernetes read-only và template env. Bổ sung bảng rủi ro/quyền ngắn cho từng server trong tài liệu kiến trúc để hỗ trợ review.

Tái sử dụng MCP nội bộ InsightHub làm server thứ năm với health/document metadata, phục vụ các day sau. Không tạo server trùng chức năng hoặc nhận bonus custom FastMCP. Should-have thêm AWS MCP và Nice-to-have Terraform MCP không nằm trong implementation này. AWS role/SSO chỉ áp dụng khi chọn nhánh AWS. Không triển khai Terraform/Helm/EKS, pipeline deployment, Grafana/Alertmanager, Slack bot hoặc gateway của Day 03-06. Không nâng dependency ứng dụng chỉ để tích hợp MCP.

## 2. Kiến trúc dự kiến

```text
Codex host (một host được chọn)
  +-- MCP client -> Filesystem server -> checkout source Day 02 sạch, /project:ro
  +-- MCP client -> Docker server     -> Docker lab, chỉ tool đọc được chọn
  +-- MCP client -> Kubernetes server -> kind / namespace insighthub / mcp-readonly
  +-- MCP client -> Prometheus server -> Prometheus local -> API + worker metrics
  +-- MCP client -> InsightHub server -> API health + document metadata

MCP Inspector -> lần lượt cùng bốn server, cùng launch config và quyền
CLI/HTTP      -> baseline, đối chiếu độc lập và thao tác operator của lab
```

Bốn process/server có identity, pin và trace riêng. Docker dùng Gateway chính chủ với catalog POCI tùy chỉnh của project, Docker CLI pin digest và proxy HTTP read-only riêng của lab; gateway được tính là một backend Docker. Backend bổ trợ không được thêm vào `docker-compose.yml` mặc định: dùng Compose override Day 02; Kubernetes lab có lifecycle riêng. `docker compose config --services` không bật override vẫn trả đúng năm service Day 01.

Host chính là Codex. Template và helper xử lý đường dẫn có dấu cách; không chép đường dẫn máy giảng viên vào cấu hình dùng chung. Chỉ ghép các server Day 02 vào config project được trust, giữ cấu hình host hiện có. Nếu app cần reload/phiên mới để nhận MCP, thực hiện trước khi thu host evidence; CLI `list` đơn thuần chưa đạt MH3.

### 2.1. Backend và pin dự kiến

Metadata upstream được tra cứu ngày 17/09/2026. Các pin dưới đây được khóa trong source; kết quả runtime nằm ở Execution_Report Day 02.

| Thành phần | Pin triển khai | Cách dùng và tiêu chí chốt |
|---|---|---|
| Filesystem | `@modelcontextprotocol/server-filesystem@2026.8.31` | Container stdio, chỉ mount checkout source sạch tại `/project:ro`; npm lock/integrity |
| Docker | `docker/mcp-gateway v0.43.3` + `docker:29.7.2-cli` digest | Gateway stdio chính chủ, POCI argv cố định; proxy HTTP chỉ cho phép đọc lab. Gateway là prerelease đã pin/checksum và kiểm thử |
| Kubernetes | `containers/kubernetes-mcp-server v0.0.66` | Binary stdio đúng OS/architecture, checksum; kubeconfig SA riêng, core toolset/read-only |
| Prometheus MCP | `prometheus/prometheus-mcp v0.18.0` | Binary stdio/checksum; endpoint lab cố định, chỉ công cụ query cần thiết |
| Inspector | `@modelcontextprotocol/inspector@2.7.0` | Cài từ lockfile, chạy local có authentication, screenshot từng server |
| Cluster lab | `kind v0.33.0` | Binary checksum; node image digest theo release tương thích, một node |
| Prometheus lab | `prometheus v3.14.0` | Image digest; cấu hình scrape tối thiểu, không bật admin/lifecycle API |

Trước khi kích hoạt host: ghi exact artifact URL, version, image digest hoặc checksum, dependency lock, OS/architecture và observed protocol vào manifest. Kiểm tra `--help`, tool schema và tool list của đúng artifact. Không dùng `latest`, `npx` tải bản mới khi mở phiên, hoặc suy protocol từ phiên bản SDK. Nếu ứng viên không đạt compatibility/quyền, cập nhật lựa chọn trong plan và review thay đổi trước khi đổi backend.

Nguồn chọn backend: [Filesystem upstream](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem), [npm metadata](https://registry.npmjs.org/@modelcontextprotocol/server-filesystem/2026.8.31), [Docker Gateway](https://github.com/docker/mcp-gateway/releases/tag/v0.43.3) và [catalog chính chủ](https://github.com/docker/mcp-registry), [Kubernetes release](https://github.com/containers/kubernetes-mcp-server/releases/tag/v0.0.66), [Prometheus MCP release](https://github.com/prometheus/prometheus-mcp/releases/tag/v0.18.0), [Inspector](https://modelcontextprotocol.io/docs/tools/inspector).

### 2.2. Quyền thực thi và dữ liệu lab

| Backend | Thiết kế | Kiểm chứng bắt buộc |
|---|---|---|
| Filesystem | Một project root; Docker MCP Gateway chỉ mount snapshot source sạch read-only, không mount HOME, Docker socket hay runtime secrets. Runtime credentials nằm ngoài snapshot | Đọc README được; path ngoài `/project` và traversal bị chặn; write tool không được expose; file canary không đổi |
| Docker | Ba tool POCI có argv đọc cố định, không nhận shell/args từ model. Proxy enforce project filter, hai log targets, không expose inspect/env hoặc API mutation | Danh sách tool thực không có mutation; direct MCP call tới tool ghi bị từ chối; container canary giữ nguyên |
| Kubernetes | SA `mcp-readonly`; ClusterRole chỉ get/list/watch trên pods, pods/log, events, services, deployments, replicasets; RoleBinding trong `insighthub` | Có quyền đọc pod lab; không delete/create/patch, exec, đọc secrets, đọc namespace khác hay đổi context |
| Prometheus | URL cố định tới Prometheus lab; chọn query/range query/targets; tắt TSDB admin và lifecycle ở backend, hạn chế toolset tại server và host | Có series thật; không query sang URL khác; tool admin bị chặn; response/timespan có giới hạn cấu hình được kiểm chứng |

Filesystem upstream có cơ chế Roots thay thế allowlist. Vì vậy phải kiểm tra `list_allowed_directories` sau host kết nối; mọi Roots update phải giữ root lab; chỉ chấp nhận `/project`. Mount/sandbox mới là lớp chặn truy cập host, không dùng Roots làm bảo đảm độc lập. [Nguồn Filesystem](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem).

Docker Gateway không nhận Docker socket trong tool container; Docker CLI gọi proxy loopback. Proxy giữ socket, chỉ forward GET allowlist, áp project filter cố định, loại Env/Labels/Mounts và chặn mutation. Socket `:ro` tự nó không hạn chế Docker API. Proxy là helper kiểm soát quyền cho backend, không phải MCP server tự viết. Host dùng approval chuẩn cho tool POCI thiếu readOnlyHint; không bỏ approval hay secret scanning. [Docker catalog](https://github.com/docker/mcp-registry), [Docker daemon security](https://docs.docker.com/engine/security/protect-access/).

Kubeconfig chứa một context và token SA có hạn, file permission 0600, nằm ngoài Filesystem root và Git. Operator dùng kubeconfig quản trị riêng để tạo lab; MCP không nhận kubeconfig admin. ClusterRole được bind bằng RoleBinding để giới hạn namespace; tên ClusterRole không đồng nghĩa cấp quyền toàn cluster. Acceptance `can-i` phải có `-n insighthub`, kiểm tra thêm namespace khác. [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).

Prometheus MCP có cả công cụ quản trị; phải chọn toolset và kiểm tra direct denied call. Không mặc định mọi Prometheus tool đều read-only. Giới hạn/truncation có thể được tool argument thay đổi thì chỉ ghi là giới hạn vận hành, không mô tả như hard security cap. [Tài liệu đúng tag v0.18.0](https://raw.githubusercontent.com/prometheus/prometheus-mcp/v0.18.0/README.md).

## 3. Requirement-to-evidence mapping

| ID | Triển khai | Expected result / evidence |
|---|---|---|
| MH1 | TOML/JSON templates, generator và config project cho Codex, Claude Code, Antigravity IDE | Parse thành công, config path/hash đã làm sạch, host khởi động đủ server |
| MH2 | Bốn entry/backend Filesystem, Docker, Kubernetes, Prometheus | Manifest ánh xạ server -> backend -> artifact -> tool; đủ bốn backend khác nhau |
| MH3 | Trong phiên Codex, gọi ít nhất một tool thành công/backend | Bốn host traces có tên tool, args, output, thời điểm, host/model/version, backend identity |
| MH4 | Pin package/binary/container và dependency locks | Không floating version; checksum/digest đầy đủ, launch không auto-update |
| MH5 | Namespace và ServiceAccount `mcp-readonly` | `kubectl --context <lab-admin> get sa mcp-readonly -n insighthub` thành công |
| MH6 | ClusterRole read-only + RoleBinding theo namespace | YAML cùng allowed/denied tests bằng chính kubeconfig SA; `get pods=yes`, `delete pods=no` |
| MH7 | Filesystem một root, kiểm tra path thực và Roots | Call đọc project thành công; ngoài project/traversal/symlink canary bị từ chối |
| MH8 | Computer Use điều khiển Inspector cho từng server | Ít nhất bốn screenshot: connection, tools/list, tools/call và output thành công |
| MH9 | Một crashed-container debug case qua Docker MCP | `debug-session-day2.md`: timeline, evidence, giả thuyết, RCA, remediation và retest |
| MH10 | Mini-quiz 10 câu, điểm thực >=7/10 | Bài làm/điểm trên quiz lớp; solution có đáp án và giải thích để đối chiếu |
| SH2-4 | Cố định context/namespace, Kubernetes read-only, env template | Config/negative tests và runbook tái lập |
| NH threat model | Bảng quyền/rủi ro của bốn server trong Architecture | Mỗi server có tài sản, threat, enforcement và test tương ứng |
| Quy ước chung | Prompt pack >=3, branch/commit/PR và self-check | Năm prompt có mục đích rõ; linked evidence; bảy câu self-check có giải thích |

Repo hiện không cung cấp nội dung/link quiz form Day 02. Khi triển khai, chuẩn bị bộ giải thích 10 câu theo learning objectives và trả lời quiz chính thức khi có đề. Bộ câu hỏi luyện tập hoặc answer key không được ghi thành điểm quiz lớp. MH10 chỉ đóng khi có bằng chứng điểm thực; không để ảnh hưởng tiến độ các hạng mục kỹ thuật độc lập.

Learning evidence đi cùng integration: giải thích Host/Client/Server; phân biệt Tools/Resources/Prompts bằng capabilities thực của server; so sánh stdio với Streamable HTTP; đọc RBAC và chẩn đoán một lỗi kết nối bằng Inspector. Có thể xem resource/prompt khi backend hỗ trợ, không tự thêm capability để đủ ba primitives. Runbook bao gồm lỗi sai executable/path, token hết hạn, sai namespace và port conflict; chỉ inject trong lab. Bộ self-check trả lời đủ bảy câu mục 6.9.

## 4. Các bước triển khai và kết quả dự kiến

| Bước | Công việc | Đầu ra / gate chuyển bước |
|---|---|---|
| 1. Review plan | D2-P01/P02; kiểm tra đủ MH, pin, quyền, file scope và test matrix | Plan được duyệt trước cài dependency, tạo cluster hay sửa runtime config |
| 2. Baseline/branch | Tạo `day2-mcp` từ main đã xác minh; chạy smoke/regression; ghi source hash và phiên bản | Baseline tái lập; không dùng dữ liệu lab khác |
| 3. Pin và preflight | Cài tooling vào thư mục riêng; kiểm checksum, architecture, flags, schemas; chốt manifest | Mọi artifact dùng được; không còn placeholder trong config được kích hoạt |
| 4. Lab dependencies | Compose project/ports riêng; kind một node; workload mẫu; Prometheus scrape API/worker; RBAC/SA/kubeconfig | Năm service app healthy; pod lab Running; scrape targets up; SA allowed/denied đúng |
| 5. Bốn MCP servers | D2-P03; launch cấu hình tối thiểu; lock dependencies; parse config; SDK list/call, negative tests | Bốn backend có calls thật; không cấp thêm quyền để né lỗi |
| 6. Host integration | Nạp config Codex; kiểm tra context; gọi bốn tool trên backend live bằng model/host | Trace host riêng với SDK evidence; output khớp dữ liệu lab |
| 7. Review/permissions | D2-P04; review diff, pin, output, deny tests; chạy regression Day 01 và MCP starter | Findings trong scope được xử lý; không giảm assertions/verifier |
| 8. Browser/debug | D2-P05; Inspector bốn server, UI regression và crashed-container RCA | Screenshot, case study có timestamps và xác minh phục hồi |
| 9. Bàn giao | Runbook, Architecture, prompt pack/evidence, quiz/self-check, commits, PR description | Ma trận MH có bằng chứng; chỉ mục bài giải rõ ràng; cleanup lab đúng project |

Khi triển khai, stop/start/fault injection chỉ nhắm Compose project và cluster vừa tạo; teardown chỉ xóa tài nguyên lab được ghi nhận, không prune Docker hoặc xóa volumes của project khác.

## 5. Debug case dự kiến

Một container kiểm tra cấu hình trong profile `day2-debug` yêu cầu biến `DAY2_REQUIRED_VALUE`. Lượt incident cố ý thiếu biến nên process log mã lỗi rõ và exit khác 0; không chứa secret. Đây là fault injection có kiểm soát, không tuyên bố là bug ứng dụng Day 01.

1. Operator khởi tạo incident, ghi thời điểm bắt đầu và ID container.
2. Codex dùng Docker MCP list trạng thái rồi đọc log giới hạn của đúng ID; operator đọc cấu hình mẫu trong source để đối chiếu giá trị hợp lệ.
3. Case study đối chiếu ít nhất hai giả thuyết với log/config; tách kết luận model khỏi phần kiểm chứng của học viên.
4. Agent đề xuất diff/remediation; operator áp dụng biến cấu hình đúng bằng CLI trong lab. MCP read-only không tự restart hoặc recreate.
5. Docker MCP xác nhận container thay thế Running/healthy hoặc hoàn thành exit 0 theo workload; ghi thời điểm phục hồi.
6. Dùng cùng container incident chưa sửa cho lượt CLI baseline và lượt MCP; báo riêng thời gian CLI lấy evidence và host MCP gồm startup/model/approval/RCA. Thừa nhận hiệu ứng biết trước nguyên nhân, không suy ra phần trăm cải thiện chung từ một case.

Output: `debug-session-day2.md` chứa symptoms, environment, timeline, tool/input/output references, hypothesis table, root cause, fix, retest và bài học. Không đưa nội dung hội thoại điều hành dự án vào case study.

## 6. Kế hoạch kiểm thử

| Nhóm | Cases chính | Pass khi |
|---|---|---|
| Static/config | Parse TOML/JSON cho ba host, đủ năm server, pins, paths có space, không secrets/floating versions | Generator tái lập, manifests và config thống nhất |
| MCP compatibility | Discovery/initialize phù hợp revision, tools/list, tools/call, discovery/call errors; backend unavailable qua unit test | Ghi observed protocol từng server; lỗi rõ, không trả fixture thành live |
| Filesystem | Read README; path ngoài root; traversal; kiểm tra allow-list; gọi write tool không có trong discovery; kiểm tra canary | Chỉ project root đọc được, canary không bị sửa |
| Docker | List đúng lab, logs có bound; unavailable daemon; direct mutation denied | Không công cụ ghi; không lộ env, credentials hoặc container khác trong evidence |
| Kubernetes | SA đúng identity; get/list pods; delete/create/patch/exec/secrets/namespace khác denied | RBAC thực thi ngay cả khi bypass host tool filter |
| Prometheus | Targets/API/worker up; instant/range query; so sánh HTTP tại cùng thời điểm; admin denied | Series có nguồn thật; empty khác zero; query không đổi backend |
| Host/model | Bốn backend connected và call thành công trong Codex | Tool traces đủ args/output/timestamp; native shell không thay MCP call |
| Regression | API/worker tests, live Day 01 contract, lint/typecheck, MCP starter, verifier tests | Giữ assertions và năm service mặc định; upload/chat/retry không đổi |
| Evidence | Source/config hashes, log/screenshot manifests, secret review | Tái lập được; không dùng kết quả cũ để xác nhận nguồn mới |

Giữ `scripts/verify-day-2.sh` và assertions của verifier. Chạy SDK tests và live verifier của MCP mẫu theo [verification contract](../../scripts/VERIFICATION_CONTRACT.md); chúng chỉ chứng nhận contract mẫu. Bổ sung test runner cho bốn vendor backend dưới `tests/milestones/day2/`, không sửa verifier để tự chấm đủ milestone. PASS của checker/verifier không thay MH3, MH8, MH9 hoặc MH10.

### Computer Use & Control Browser

| Case | Thao tác bằng UI | Kết quả dự kiến |
|---|---|---|
| B01 | Inspector kết nối Filesystem, list tools và đọc README | Output đúng checkout; screenshot không chứa token |
| B02 | Inspector kết nối Docker, đọc logs container lab | Đúng log; status được đối chiếu bằng host trace, không gọi mutation |
| B03 | Inspector kết nối Kubernetes, invoke tool liệt kê pods với namespace | Trả pod lab bằng identity SA read-only |
| B04 | Inspector kết nối Prometheus, invoke query health API/worker | Hai series up=1; SDK/HTTP đối chiếu riêng tại timestamp cố định |
| B05 | Inspector thực hiện read ngoài FS root và K8s ngoài namespace với canary | Bị từ chối đúng lớp; lưu output đã làm sạch |
| B06 | Browser mở InsightHub, upload Markdown bằng picker, chờ ready rồi chat | UI hoạt động, có answer/source; fixture được ghi đúng phạm vi |
| B07 | Browser mở Prometheus Targets/Query sau thao tác ứng dụng | API/worker targets up, series có dữ liệu; không thêm dashboard |
| B08 | Browser reload InsightHub sau debug case | App tiếp tục hoạt động; không regression do lab MCP |

Inspector dùng cùng launch definitions, quyền và backend với Codex. Giữ authentication, chỉ loopback; không tắt security để vượt lỗi kết nối. Không dùng screenshot CLI thay cho Inspector. Browser E2E dùng Computer Use/Control Browser; HTTP/SDK chỉ đối chiếu độc lập.

## 7. Phạm vi artifact dự kiến

| Artifact | Mục đích |
|---|---|
| `tools/mcp/day2/` | Manifest backend, lockfiles, launcher/config generator; cách ly dependency với MCP mẫu |
| `tools/mcp/day2/{codex.config.toml,claude.mcp.json,antigravity.mcp_config.json}.template` | Template portable; config thực sinh local, không commit token hoặc đường dẫn cá nhân |
| `tools/mcp/day2/.env.example` | Giá trị lab local cố định; kubeconfig/context do generator tạo, không có credentials |
| `docker-compose.day2.yml` | Docker read proxy, Prometheus lab và debug profile; không đổi năm service mặc định |
| `infra/k8s/mcp-readonly/` | Namespace, SA, ClusterRole, RoleBinding và manifest workload mẫu; chưa là deployment Day 03 |
| `tools/mcp/day2/lab/` | kind config và Prometheus scrape config tối thiểu |
| `tests/milestones/day2/` | Config, permission, SDK live và fault-injection assertions |
| `AGENTS.md`, `Makefile` | Context Day 01-02, lệnh tái lập và loại runtime secrets/artifacts local |
| `ai-prompts/day2.md` | Năm prompt dành cho học viên, hướng dẫn dùng và liên kết evidence khi thực hiện |
| `debug-session-day2.md` | Case study đã thực hiện, không chứa kết quả dự kiến dưới nhãn kết quả thật |
| `docs/day2/` | README, Architecture_and_Decisions, Runbook, Review_and_Self_Check, Quiz_and_Answers, PR_Description |
| `docs/evidence/day2/`, `evidence/day2.json` | Evidence được chọn, đã làm sạch; report verifier partial giữ đúng ý nghĩa |

`api/`, `web/`, `ingestion-worker/` và DB schema không nằm trong diff tính năng dự kiến. Lỗi mới ngoài Day 02 được ghi trong báo cáo kỹ thuật để quyết định riêng, không tự sửa. Không đưa báo cáo điều hành hoặc ghi chú không phục vụ nghiệm thu Day 02 vào bộ solution học viên.

## 8. Prompt workflow và commit strategy

Dùng [năm prompt Day 02](../../ai-prompts/day2.md) theo thứ tự: kiến trúc/context; planning và design review; triển khai; review/kiểm thử quyền; debug/browser E2E và bàn giao. Prompt là hướng dẫn học viên thực hiện bài. Khi dùng thực tế mới bổ sung host/model/version/auth/time, quyết định review và evidence; không ghi metadata hoặc kết quả giả.

Bốn commit dự kiến trên `day2-mcp`:

1. `chore(day2): define MCP scope and student workflow` - plan, prompt pack, context Day 01-02 và danh sách artifact.
2. `feat(mcp): integrate pinned backends with scoped local lab access` - manifests/locks, host config, lab, SA/RBAC và tests đi cùng implementation.
3. `test(mcp): verify live backends and permission boundaries` - live harness, fault injection, negative/regression tests và điều chỉnh findings trong scope.
4. `docs(day2): add reproducible solution and acceptance evidence` - runbook, case study, Inspector/host evidence, quiz/self-check và PR description.

Mỗi commit có một mục đích, không commit rỗng để đủ số. Fix phát sinh được đưa vào commit phù hợp trước khi công bố; không viết lại lịch sử đã dùng chung nếu chưa được yêu cầu. Giữ nguyên ba commit Day 01. PR dự kiến: `[Day 2] Integrate MCP backends with read-only lab access`. Review final diff, secret scan và kiểm thử trước khi đề nghị merge; không tự merge/push khi chưa được yêu cầu.

## 9. Definition of Done

- Có đủ mười MH với evidence tương ứng; điểm quiz thật được phân biệt với answer key.
- Bốn backend pinned, host calls và Inspector calls thành công trên backend live; quyền đọc/deny được kiểm chứng.
- Debug case được tái tạo và phục hồi, RCA dựa trên output thật, đo thời gian có phạm vi rõ.
- Runbook cho phép học viên dựng lab, kết nối, test và teardown từ checkout sạch.
- Regression Day 01 đạt; không thay schema/contracts hoặc triển khai tính năng ngày sau.
- Prompt pack, source, commits, PR description và evidence nhất quán với bản nghiệm thu.

Trạng thái nghiệm thu thực tế và các mục chưa đủ bằng chứng được ghi tại `docs/day2/Review_and_Self_Check.md`.
