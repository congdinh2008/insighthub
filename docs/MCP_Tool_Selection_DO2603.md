# Lựa chọn MCP cho InsightHub DO2603

**Ngày truy cập và kiểm chứng nguồn: 08/09/2026. Phạm vi: Day 1-7, InsightHub local lab.**

MCP read-only trong repo là starter minh họa. Running project Day 2 vẫn yêu cầu 4+ server Filesystem/Docker/K8s/Prometheus và tái sử dụng K8s/Prometheus Day 4/5. Dùng native file tools và CLI cho công việc trong checkout; trong dự án thực tế không đặt chỉ tiêu số lượng server, nhưng bài học Day 2 giữ phạm vi 4 tích hợp để luyện các ranh giới quyền khác nhau. SDK chính thức, protocol và quyền thực thi được kiểm chứng riêng.

## 1. Kết quả nghiên cứu phiên bản

| Thành phần | Phiên bản/nguồn đã xác minh | Kết luận cho lab |
|---|---|---|
| MCP specification | **2026-07-28**, Current theo [versioning chính thức](https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning) | Đã phát hành, không gọi là roadmap hoặc dự đoán |
| TypeScript SDK v2 | [server 2.0.0](https://github.com/modelcontextprotocol/typescript-sdk/releases/tag/@modelcontextprotocol/server@2.0.0), phát hành 27/07/2026 UTC; GitHub API `prerelease=false`; npm xác nhận server/client 2.0.0 | Pin bản này và dùng `serveStdio` để phục vụ cả modern/legacy |
| TypeScript SDK v1 | [1.30.0](https://github.com/modelcontextprotocol/typescript-sdk/releases/tag/1.30.0), 27/07/2026; [constants tại tag](https://github.com/modelcontextprotocol/typescript-sdk/blob/1.30.0/src/types.ts) vẫn lấy 2025-11-25 là latest của SDK v1 | Chỉ làm client kiểm chứng compatibility; không gắn nhãn v1 hỗ trợ 2026 |
| Python SDK | [v2.2.0](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.2.0), 07/09/2026; [README tại tag](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/README.md) mô tả v2 là stable, hỗ trợ 2026 và các revision trước | Đã xác minh nguồn, chưa cài/test tại đây. Không thêm runtime thứ hai chỉ vì release mới hơn |
| Starter implementation | server/client 2.0.0, Zod 4.5.4, legacy client 1.30.0, [package-lock](../tools/mcp/package-lock.json) | Node 24.16.0/npm 11.13.0 thực thi đạt; Node >=22 là yêu cầu package, không phải mọi version đã test |

Ghi release/tag và integrity trong lockfile; kiểm tra metadata của đúng phiên bản và protocol thực tế trên host trước khi cấu hình chung cho lớp.

## 2. Protocol mới và handshake cũ

| Cơ chế | Legacy 2025-11-25 trong lab | Modern 2026-07-28 trong lab |
|---|---|---|
| Mở kết nối | `initialize` rồi `notifications/initialized` | `server/discover`; không handshake cũ |
| Version/capabilities | Thương lượng đầu phiên | Envelope `_meta` trên request |
| Server SDK entry | `serveStdio` nhận legacy opening | Cùng factory, nhận modern opening |
| Kết quả tool | Content/structuredContent | Wire có `resultType=complete`, SDK xử lý trường protocol |
| Tool quyền đọc | Server allowlist + kiểm tra arguments | Cùng policy và code ứng dụng |

[Bản tổng quan protocol 2026](https://modelcontextprotocol.io/specification/2026-07-28/basic) xác định cấu trúc request/result; [SDK migration](https://github.com/modelcontextprotocol/typescript-sdk/blob/main/docs/migration/support-2026-07-28.md) mô tả opt-in. `new McpServer().connect(new StdioServerTransport())` vẫn đi theo legacy ngay cả trên v2. Starter dùng `serveStdio(factory, {legacy:"serve"})`; client test pin revision hoặc chọn legacy rõ ràng. Modern discovery không phải quyền truy cập và không thay `tools/list`.

Các cập nhật cần đưa vào bài Day 2: protocol mới bỏ HTTP session/handshake, dùng `subscriptions/listen`, đưa Tasks sang extension, có MRTR và cache hints. Roots/Sampling/Logging đã deprecated; HTTP+SSE cũ cũng deprecated. Đây là thay đổi đã ghi trong [changelog chính thức](https://modelcontextprotocol.io/specification/2026-07-28/changelog), không phải danh sách mọi tính năng starter triển khai. Demo protocol trong lớp chọn stdio và tool đọc có giới hạn; chạy đủ bốn tích hợp trong running project; remote chia sẻ nhiều người mới cần đánh giá Streamable HTTP, auth, issuer và policy riêng.

## 3. Compatibility đã chạy và phần chưa chạy

| Client/host | Version chính xác | Transport/protocol | Bằng chứng |
|---|---|---|---|
| Official TS client, modern pin | `@modelcontextprotocol/client@2.0.0` | stdio / 2026-07-28 | Đạt: discovery, tools/list, ba tools/call |
| Official TS client, auto | 2.0.0 | stdio / 2026-07-28 | Đạt; SDK có probe bằng process phụ |
| Official TS client, legacy | 2.0.0 | stdio / 2025-11-25 | Đạt handshake cũ + tools/list/call |
| Official TS v1 client | `@modelcontextprotocol/sdk@1.30.0` | stdio / 2025-11-25 | Đạt bằng client v1 thật, không giả lập wire bằng tay |
| Claude Code local | 2.1.263 từ `claude --version` | Cấu hình stdio được tài liệu hỗ trợ | Chưa chạy tool qua model/host; không suy protocol từ version CLI |
| Codex CLI local | 0.153.4 từ `codex --version` | `codex mcp add --help` xác nhận stdio | Chưa chạy tool qua model/host; không khẳng định modern negotiation |
| Antigravity | Ghi product/build của học viên | Helper JSON và rule template có sẵn | Chưa chạy host/model roundtrip; không suy protocol từ SDK |
| Claude Desktop | Không đo version trong task | JSON cấu hình có thể sinh đường dẫn tuyệt đối | Planned host verification, không có version giả |
| Python client 2.2.0 | Chỉ xác minh source release | Upstream công bố hỗ trợ 2026 và legacy | Planned runtime test, không ghi đạt |
| Các revision legacy khác | SDK v1 constants có 2025-06-18, 2025-03-26, 2024-11-05, 2024-10-07 | Không được smoke này ép dùng | Chưa xác nhận thực thi từng revision |
| Vendor MCP trong bảng dưới | Tag được dẫn riêng | Không suy protocol từ release mới | Source-verified, chưa chạy end-to-end |

Kết quả SDK dùng **HTTP fixture local + MCP process thật**. Nó không chứng minh API/Compose live đã sẵn sàng. `--live` chạy cùng SDK against API hiện có và in `backend_mode:"live"`. Cấu hình host không tự thay đổi sau khi chạy smoke.

## 4. Matrix tối thiểu theo công việc và ngày học

Đây là đề xuất triển khai cho DO2603, không phải benchmark tốc độ giữa các sản phẩm.

| Ngày / kết quả | Native tools/CLI ưu tiên cho Claude Code, ChatGPT-Codex và Antigravity | MCP nhỏ nhất hữu ích | Điều kiện và cách đánh giá |
|---|---|---|---|
| Day 1: refactor + tests | Đọc/sửa file, `rg`, git diff, test runner, Compose CLI | Không bắt buộc | Hiểu flow và tự chạy test trước; AI đề xuất diff có thể review. Không cần filesystem MCP trùng quyền |
| Day 2: contract và quyền tool | CLI để kiểm chứng HTTP baseline; SDK test client | 4+ MCP integrations theo spec; InsightHub starter2 tools chỉ minh họa | Đo tools/list/call; cố gọi tool disabled phải fail; đọc metadata không lộ content |
| Day 3: IaC + CI | Terraform fmt/validate/plan, workflow validation, `gh` khi cần repo remote | HashiCorp registry-only nếu cần tra provider/module; GitHub read-only khi gh không đáp ứng flow host | Review plan và diff bằng quy trình riêng; MCP không tự apply hoặc merge |
| Day 4: quan sát lỗi | Prometheus UI/HTTP, promtool, CLI log có giới hạn | Bật `prometheus_summary` trên starter; Grafana nếu cần dashboard + nhiều datasource | So sánh số đo với query gốc; null nghĩa thiếu series; metric aggregate chưa phải RCA |
| Day 5: incident/ChatOps | Snapshot trạng thái/log đã lọc, runbook, workflow bot sẵn có | Tái sử dụng K8s/Prometheus MCP đã tích hợp Day 2 trên cluster project | Thu bằng chứng trước, AI giải thích sau. Restart, rollback và gửi incident update là hành động riêng |
| Day 6: governance/FinOps | Scan secret, dependency/IaC policy, billing export hoặc dữ liệu lab | AWS Knowledge cho tài liệu; AWS MCP API chỉ ở nhánh có IAM riêng | Không mount credential vào starter. Không nhầm docs search với quyền đọc tài khoản |
| Day 7: demo tái lập | Chạy verifier/test, lưu lock và evidence | Chỉ các server đã chứng minh cần thiết | Báo SDK/protocol/backend thật; không cài thêm vendor vào ngày demo |

Claude Code có tool search tải schema theo nhu cầu và điều kiện phụ thuộc provider/model; xem [tài liệu Claude](https://code.claude.com/docs/en/mcp). Điều đó giảm context, không giảm quyền của tool. Codex có `enabled_tools`/`disabled_tools` trong [MCP config](https://learn.chatgpt.com/docs/extend/mcp?surface=cli). Dùng lọc ở host và server cùng nhau; không lấy cơ chế discovery làm security boundary. Hai tool ngắn của starter chưa cần gateway hoặc code execution orchestration.

## 5. Vendor sources, version và lý do lựa chọn

Tất cả URL dưới đã truy cập ngày 08/09/2026. “Source-verified” nghĩa là đã đọc nguồn/tag, **không** có nghĩa binary hoặc hosted service đó đã được chạy thử.

| Nhà cung cấp/repo | Version và ngày release UTC đã đối chiếu | Mechanism hữu ích, lựa chọn cho lab |
|---|---|---|
| [GitHub official MCP](https://github.com/github/github-mcp-server/blob/v1.12.0/README.md) | [v1.12.0](https://github.com/github/github-mcp-server/releases/tag/v1.12.0), 03/09/2026 | Local binary/container có `--read-only`/`GITHUB_READ_ONLY=1`, `--tools` hoặc toolsets. Read-only ưu tiên hơn tool ghi được chỉ định. Dùng token tối thiểu cho repo cần đọc; gh/native CLI thường đủ cho một checkout |
| [Docker MCP Gateway](https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/) | [v0.43.3](https://github.com/docker/mcp-gateway/releases/tag/v0.43.3), 16/07/2026, **prerelease=true** | Gateway quản lý/routing MCP servers, không đồng nghĩa tool đọc container. Profiles, catalog và kiểm soát container hữu ích khi vận hành nhiều server; đánh giá khi quản lý bốn backend Day 2; không lấy gateway thay server đọc container |
| [containers/kubernetes-mcp-server](https://github.com/containers/kubernetes-mcp-server/blob/v0.0.66/README.md) | [v0.0.66](https://github.com/containers/kubernetes-mcp-server/releases/tag/v0.0.66), 31/07/2026 | `--read-only`, `--disable-multi-cluster`, `--toolsets=core`, kubeconfig riêng; deny Secret qua cấu hình và RBAC. Dùng cluster local chuẩn bị Day 2, tái sử dụng Day 3/5; không cấp cluster-admin |
| [HashiCorp Terraform MCP](https://raw.githubusercontent.com/hashicorp/terraform-mcp-server/v1.3.0/README.md) | [v1.3.0](https://github.com/hashicorp/terraform-mcp-server/releases/tag/v1.3.0), 26/08/2026 | `stdio --toolsets=registry`, không TFE_TOKEN; tra provider/module. `--tools` và `--toolsets` không dùng đồng thời. `ENABLE_TF_OPERATIONS=false` không phải bảo đảm mọi HCP tool đều read-only |
| [Grafana official MCP](https://github.com/grafana/mcp-grafana/blob/v1.3.0/README.md) | [v1.3.0](https://github.com/grafana/mcp-grafana/releases/tag/v1.3.0), 28/08/2026 | `--disable-write` bỏ tool ghi và raw SQL; không thêm `--enable-query` nếu chưa kiểm tra quyền datasource. Service account chỉ đọc, scope datasource hẹp. Chọn khi dashboard/datasource correlation đem lại giá trị vượt ba query local |
| [AWS Knowledge MCP](https://awslabs.github.io/mcp/servers/aws-knowledge-mcp-server) | Managed GA, không có semantic version để pin local | Docs/code/API availability; [upstream](https://github.com/awslabs/mcp/tree/main/src/aws-knowledge-mcp-server) ghi không cần auth, có rate limit. Ưu tiên khi chỉ tra cứu, không cần tài khoản cloud |
| [AWS Documentation MCP](https://awslabs.github.io/mcp/servers/aws-documentation-mcp-server) | `awslabs.aws-documentation-mcp-server`, source project version **1.2.1** | Fallback local docs server nếu host/network cần. Version đọc từ source, chưa xác nhận wheel hoặc runtime, chưa pin vào lab |
| [AWS API MCP](https://awslabs.github.io/mcp/servers/aws-api-mcp-server) | `awslabs.aws-api-mcp-server`, source project version **1.5.5** | Upstream ghi superseded bởi AWS MCP Server, có [migration guide](https://github.com/awslabs/mcp/blob/main/src/aws-api-mcp-server/MIGRATION.md). Không chọn làm cài mới mặc định |
| [AWS MCP Server](https://docs.aws.amazon.com/agent-toolkit/latest/userguide/mcp-server.html) | Managed endpoint, không gán version giả | Docs/service information có thể không auth; gọi API, chạy Python sandbox và curated skills cần IAM. Nhánh vận hành cần scope IAM và audit riêng, ngoài starter local |

Các bản AWS local trong bảng là version của source project đã đối chiếu, không chứng minh wheel hoặc runtime đã được cài/test. Managed endpoint không có semantic version để pin như binary local.

Một thay đổi đáng chú ý của [Docker v0.43.1](https://github.com/docker/mcp-gateway/releases/tag/v0.43.1) là guard URL/redirect, auth HTTP, kiểm soát bind mount và xác minh digest đối với Docker MCP images. Cần kiểm tra catalog/profile thực tế trước khi dùng; không sao chép cấu hình mount socket/credentials từ bài cũ. Gateway vẫn không tự biến server bên dưới thành read-only.

Không dùng số version của các repo khác nhau để xếp hạng độ trưởng thành. Không thêm filesystem MCP, Docker gateway, K8s, Terraform, AWS và Grafana cùng lúc nếu bài chỉ hỏi API InsightHub có sống hay không.

## 6. Starter thực thi và cấu hình host

```sh
# Từ repo root:
npm ci --prefix tools/mcp --ignore-scripts
npm --prefix tools/mcp test
node tools/mcp/smoke.mjs
node tools/mcp/smoke.mjs --live
```

Lệnh cuối cần API đang chạy; các lệnh trước không cần cloud. Smoke in protocol và backend thực tế, cần lưu kết quả mỗi lượt thực hành. [Manifest MCP mẫu](../tools/mcp/manifest.json) và [hướng dẫn cấu hình host](../tools/mcp/README.md).

Entrypoint: `node tools/mcp/src/server.mjs`. Mặc định:
- `INSIGHTHUB_API_URL=http://127.0.0.1:8000`.
- `INSIGHTHUB_MCP_TOOLS=insighthub_health, insighthub_list_documents`.
- Prometheus tắt; muốn bật cần cả flag `INSIGHTHUB_MCP_PROMETHEUS=1` và thêm `prometheus_summary` vào allowlist.

[.mcp.json.template](../.mcp.json.template) chỉ dành cho Claude project khởi chạy từ repo root. Không có credential hoặc package floating. Desktop/Codex/Antigravity dùng helper sau để in cấu hình với đường dẫn tuyệt đối của máy hiện tại:

```sh
node tools/mcp/host-config.mjs claude
node tools/mcp/host-config.mjs codex
node tools/mcp/host-config.mjs antigravity
```

Helper chỉ in stdout; người dùng ghép vào cấu hình host. Codex dùng TOML; Claude và Antigravity dùng JSON với field riêng từng host. Không tự cài vào tài khoản/host trong task này. CLI phiên bản local đã được đọc; tool roundtrip qua Claude/Codex/Antigravity chưa được xác nhận.

## 7. Quyền thực thi và giới hạn thực tế

| Kiểm soát | Enforcement trong starter |
|---|---|
| Read-only | Chỉ GET route cố định; không shell/file/tool ghi; allowlist khi đăng ký và tại service |
| Chống SSRF | Chỉ literal loopback; localhost đổi sang 127.0.0.1; từ chối DNS khác, IP lạ, userinfo/path/query, redirect |
| Bounded I/O | Deadline 1500 ms/request, hard max 5000; body 64 KiB, hard max 256 KiB; stdio 64 KiB; 4 tool calls đồng thời |
| Không lộ tài liệu | Chỉ id/status/chunk_count; bỏ filename/content/created_at, raw upstream errors và metric labels |
| Strict inputs | JSON schema và kiểm tra service; không nhận URL, headers, shell command, raw PromQL |
| Negative evidence | Client gửi trực tiếp tools/call để vượt local validation; server vẫn từ chối và không gọi upstream |
| Host policy | Hints và host filters bổ sung; không thay thế server enforcement hoặc OS/IAM/RBAC |

Giới hạn cần giữ rõ: GET có tác dụng phụ quan sát như tăng counter. `/documents` baseline chưa phân trang phía API; server chỉ cắt output và chặn body quá lớn. Query aggregate 5 phút không thể chứng minh root cause, tenant isolation hoặc SLO. Env/source do operator kiểm soát; process này không bảo vệ khỏi người có quyền sửa code/host. Không xác nhận live application từ kết quả fixture.

## 8. Quy trình kiểm tra phiên bản trước mỗi ngày học

1. Chọn mục tiêu của ngày và thử native CLI trước. Chỉ thêm MCP nếu giúp tái sử dụng tool giữa host hoặc giảm thao tác API đáng kể.
2. Kiểm tra release/tag chính thức, prerelease flag, migration/security notes và metadata registry. Với managed server ghi endpoint/access date, không tự đặt semver.
3. Tạo thay đổi pin+lock có diff; chạy negative tests và SDK smoke cả modern/legacy. Nâng SDK không được tự bỏ legacy path nếu host lớp học chưa được đo.
4. Chạy `--live` với môi trường lab; đối chiếu `backend_mode`, tool list và sample output. Với host mới ghi version thực tế và protocol quan sát, không suy từ quảng cáo compatibility.
5. Chỉ chốt thay đổi khi có lợi ích cụ thể: bản vá, capability cần thiết hoặc giảm vận hành. Nếu không, giữ pin đã đạt. Không chạy auto-update dependency mỗi ngày.

**Planned verification**, không phải cam kết release tương lai: Claude Desktop version thực tế; Claude Code/Codex gọi tool trong host; Python client 2.2.0 nếu cần đối chiếu đa ngôn ngữ; vendor runtime sau khi chốt nhu cầu, token/RBAC và artifact pin. Không có ngày phát hành tương lai nào được giả định trong matrix này.

## Kiểm chứng tích hợp bổ sung 09/09/2026
Sau khi ghép starter, main đã chạy bốn SDK smoke paths với API Compose thật trên loopback, đều đạt; output `backend_mode=live`. Node host dùng 24.19.0, build web dùng container Node24.20.0. API hiện chạy RAG_MODE=fixture, nên kết quả này chứng minh MCP/API integration, không chứng minh chất lượng real LLM. Host Claude/Codex/Antigravity và vendor MCP vẫn giữ nhãn chưa chạy như bảng trên.

## Hiệu chỉnh phạm vi09/09/2026
Matrix tối ưu tool trong công việc thực tế không có quyền thay specification học tập. Không dùng CLI để bỏ bài MCP, một server mẫu để thay 4 integrations, hoặc docs-only AWS Knowledge để chứng minh quyền AWS API. Giữ source/version/SDK research và negative tests; học viên hoàn thiện tích hợp theo spec v3.3.

## Cấu hình lớp DO2603
Mỗi học viên chọn một trong ba host Claude Code, ChatGPT-Codex hoặc Antigravity; không yêu cầu host thứ hai. [Guide setup/context/evidence và Day 6](Guide_Coding_Host_DO2603.md) là nguồn thao tác. Antigravity đã có mode xuất config; host/model roundtrip vẫn cần kiểm chứng theo build của học viên. SDK tests không thay host tests.
