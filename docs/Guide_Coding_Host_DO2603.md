# Chọn một coding host cho InsightHub DO2603

Áp dụng specification v3.3, starter 0.2.3. Chọn **một trong ba**: Claude Code, ChatGPT-Codex hoặc Antigravity. Cùng 70 Must-have và rubric; không bắt dùng host thứ hai, không chấm theo thương hiệu/model. Đổi host được phép khi giữ source/context/evidence theo từng phiên.

## 1. Chuẩn bị chung
Chạy baseline theo [GETTING_STARTED](../GETTING_STARTED.md), Node 22+ (khuyến nghị Node 24 đã pin), Python 3.11+ cho kiểm tra TOML. Ghi host/product/version, OS, model, auth mode và checkout trong ai-prompts/day1.md; không ghi token.

Hoàn thiện [AGENTS.md](../AGENTS.md): Architecture, Conventions, Commands, Constraints, Domain, References, tối đa 200 dòng. TODO starter chưa hoàn thành rubric. Bài v3.2 đã có CLAUDE.md đủ nội dung được công nhận tương đương, không làm lại refactor chỉ để đổi tên.

Claude dùng Claude Code có checkout/tools; ChatGPT dùng Codex có môi trường thực thi lab. Chat web hỏi đáp thuần túy không chứng minh code/test/MCP local. Chọn model trong host không tự đổi provider của InsightHub/bot.

## 2. Context theo host

| Host | Cách nạp |
|---|---|
| Claude Code | CLAUDE.md import @AGENTS.md |
| ChatGPT-Codex | Mở đúng checkout, AGENTS.md ở root |
| Antigravity | Customizations/Rules: tạo Workspace rule, chọn Always On, chép template bên dưới |

[Rule template Antigravity](../tools/agent/antigravity-rule.md) chỉ là nội dung để tạo rule qua UI. Hiện docs dùng .agents/rules, còn hỗ trợ .agent/rules cũ. Giữ đường dẫn/frontmatter do UI đúng build tạo; file trong tools/agent không tự được nạp. [Antigravity Rules](https://antigravity.google/docs/rules-workflows/).

Claude hỗ trợ import @AGENTS.md; Codex có discovery/override riêng. Không chép ba bản context bằng tay. [Claude memory](https://code.claude.com/docs/en/memory#agentsmd), [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Trong phiên mới, yêu cầu agent chỉ ra nguồn context và giải thích constraint retry/idempotency trước khi sửa task nhỏ. Đối chiếu file, diff và tests; tự khai “đã đọc” không đủ. Nếu Antigravity không đọc nguồn ổn định, dùng rule sinh từ AGENTS.md và kiểm tra đồng bộ, không tạo bản sao biên soạn riêng. Instructions không thay sandbox/RBAC/server allowlist.

## 3. Sinh config cho một host

Từ repo root:
~~~sh
npm ci --prefix tools/mcp --ignore-scripts
npm --prefix tools/mcp test
node tools/mcp/smoke.mjs
~~~

Chạy **một** lệnh tương ứng:
~~~sh
node tools/mcp/host-config.mjs claude
node tools/mcp/host-config.mjs codex
node tools/mcp/host-config.mjs antigravity
~~~

Helper chỉ in stdout, không cài vào host. Command/args là đường dẫn tuyệt đối, hỗ trợ space/Unicode. Sinh trên cùng máy host launch MCP, không chép đường dẫn container vào GUI. Merge server InsightHub vào cấu hình hiện có, không ghi đè toàn bộ config user.

| Host | Config | Status |
|---|---|---|
| Claude Code | .mcp.json, mcpServers JSON | claude mcp list và trạng thái/tool trong phiên |
| ChatGPT-Codex | .codex/config.toml của project đã trust hoặc ~/.codex/config.toml, mcp_servers TOML | codex mcp list; /mcp trong phiên hoặc UI của app |
| Antigravity | Workspace .agents/mcp_config.json theo docs hiện tại; xác nhận file qua View raw config | Refresh/status/tool list trong UI; CLI có /mcp |

Antigravity IDE: MCP Servers/Manage MCP Servers/View raw config. Bản 2.0: Settings/Customizations/Installed MCP Servers. Global config hiện tại ~/.gemini/config/mcp_config.json; build khác phải ghi rõ file thực và version. [Antigravity MCP](https://antigravity.google/docs/mcp).

Codex không đọc JSON .mcp.json như TOML; project config cần trust. ChatGPT web không đọc config Codex local. [OpenAI MCP](https://learn.chatgpt.com/docs/extend/mcp). Claude project scope xem [Claude MCP](https://code.claude.com/docs/en/mcp).

Mẫu chỉ expose hai tool, không thay bốn backend Day 2. Học viên mở rộng config của host đã chọn, pin từng backend; ghi source/artifact, namespace/allowlist và transport vào debug-session-day2.md. Gateway phải có mapping và calls đủ Filesystem/Docker/K8s/Prometheus.

## 4. Kiểm chứng và evidence

Ví dụ Codex, thay host/config theo lựa chọn:
~~~sh
mkdir -p tmp
node tools/mcp/host-config.mjs codex > tmp/codex-mcp.toml
python3 scripts/check-agent-setup.py --host codex --config tmp/codex-mcp.toml
~~~

Checker chỉ parse cấu trúc context/config, không chứng minh context đủ chất lượng hoặc host/server đã hoạt động. Output luôn milestone_complete=false. Bài cũ dùng --context CLAUDE.md nếu chứa sáu section. Không nộp config user có secret.

Sau khi API local chạy, dùng host gọi insighthub_health và insighthub_list_documents; lưu tool/input/output, timestamp, environment và host/model/version. Đối chiếu SDK/HTTP smoke. SDK pass không chứng nhận host tool call.

Day 2 vẫn cần từng backend: host connection/call thật, Inspector list/call, RBAC/read-only và deny ngoài scope, debug case và quiz. Stdio mặc định local; Streamable HTTP được dùng khi phù hợp với auth/quyền đã kiểm chứng. Config remote khác field: Codex url, Antigravity serverUrl. [Antigravity IDE MCP](https://antigravity.google/docs/ide/mcp).

## 5. Quyền và troubleshooting

| Vấn đề | Xử lý |
|---|---|
| JSON không nạp trong Codex | Chọn output codex, kiểm tra TOML, trust và scope |
| GUI không tìm Node/server | Sinh path trên host thật, kiểm tra quyền đọc và path tuyệt đối |
| Context không được áp dụng | Đúng checkout, rule activation, override/global rules; mở phiên mới |
| Installed nhưng không gọi được | Startup log, tool availability, credentials/RBAC và call thật |
| Tool denied | Kiểm tra đúng lớp host/server/backend; không bật full access để né lỗi |
| Protocol lệch | Ghi protocol thực quan sát được, không suy từ version SDK |
| Gateway thiếu coding traffic | Phân biệt MCP endpoint với LLM endpoint; subscription với API mode |

Ba tầng chung: read-only trong scope; mutation có review/approval; vượt scope bị chặn. Day 5 cần identity riêng và audit của bot/backend, không thay bằng nút approve trong IDE. Dùng dữ liệu giả cho negative tests; không xuất cấu hình cá nhân/secret vào bài nộp.

## 6. Day 6: giữ đủ ba workload, không bắt đổi host

InsightHub, ChatOps bot và coding workflow dùng ba virtual keys riêng. Chọn một cách cho workload thứ ba:
- Host chính hỗ trợ custom endpoint đã kiểm chứng: route coding session qua LiteLLM.
- Host chính dùng subscription hoặc không có endpoint phù hợp: dùng chính host đó xây/chạy coding client/workflow API qua LiteLLM. Workflow nhận context repo, đề xuất/review thay đổi, người học review diff và chạy test; có request/usage/budget evidence.

Cả hai phải có allowed/denied budget, attribution ba workload, model access/routing và retry/concurrency/overshoot. Key không dùng hoặc curl hỏi đáp một lần không đủ. Không bắt cài Codex khi đã chọn Antigravity/Claude, hoặc mua Claude khi chọn Codex.

Codex custom provider đặt ở user-level, riêng với project MCP config; LiteLLM cần Responses endpoint và compatibility test. [OpenAI config](https://learn.chatgpt.com/docs/config-file/config-advanced), [LiteLLM Codex](https://docs.litellm.ai/docs/tutorials/openai_codex). Không ghi đè provider hiện có của học viên.

Chưa chứng nhận custom gateway mọi build Antigravity; model selector không chứng minh traffic IDE đi qua proxy. [Antigravity Models](https://antigravity.google/docs/models). Quota subscription báo riêng khỏi API cost, không quy thành USD/request thiếu dữ liệu.

Local fixture để debug trước; real model/API với workload nhỏ để chứng minh integration. AWS giữ task/kiến thức, tạo khi cần và xóa ngay sau lượt theo [cost guide](Guide_Local_AWS_Cost_DO2603.md).

## 7. Nộp bài và phạm vi hỗ trợ

Giữ artifacts từng day; bổ sung metadata vào prompt/debug log hiện có: host/product/version, model/auth, context/config path/hash đã làm sạch, backend/tool mapping, input/output/timestamp và linked diff/tests. Không có bộ submission thứ hai theo host.

Starter có adapter/helper cho ba lựa chọn. Parser tests và SDK smoke không chứng nhận phiên model trên máy học viên. Trước lab, kiểm tra context và MCP đúng host/version; ghi phần chưa chạy trung thực. [Specification](../Running-Project-Specification-Student.md) và [verification contract](../scripts/VERIFICATION_CONTRACT.md) quyết định phạm vi hoàn thành.

