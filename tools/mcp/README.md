# InsightHub read-only MCP starter

Ngày kiểm chứng: 08/09/2026. Server chính thức dùng TypeScript SDK 2.0.0, triển khai bằng JavaScript ESM để chạy trực tiếp, không cần build. [Nghiên cứu và lựa chọn theo ngày học](../../docs/MCP_Tool_Selection_DO2603.md).

## Chạy và xác minh

Từ thư mục root của InsightHub, dùng Node 22 trở lên; đã chạy trên Node 24.16.0, npm 11.13.0:

```sh
npm ci --prefix tools/mcp --ignore-scripts
npm --prefix tools/mcp test
node tools/mcp/smoke.mjs
```

Smoke mặc định mở HTTP fixture trên loopback và khởi chạy **server stdio thật bằng SDK client thật**. Không cần Docker, API, LLM key, cloud hoặc quyền admin. Cần môi trường cho phép bind cổng loopback ngẫu nhiên. Nó không xác nhận Compose hoặc API đang chạy.

```sh
# Khi API InsightHub đã chạy tại 127.0.0.1:8000:
node tools/mcp/smoke.mjs --live

# Entrypoint để MCP host khởi chạy:
node tools/mcp/src/server.mjs
```

Entrypoint đợi JSON-RPC trên stdin và chỉ xuất JSON-RPC trên stdout. Không gõ câu hỏi trực tiếp vào terminal này. Host sẽ launch process, gọi discovery và tool.

Smoke trực tiếp qua `node` in một JSON object, exit 0 khi đạt. `backend_mode` là `fixture` hoặc `live`, `live` là boolean; `results[]` ghi SDK client, mode, protocol thực tế, methods và calls. `npm --prefix tools/mcp run smoke` có thêm npm banner. [manifest.json](manifest.json) là contract của MCP mẫu; không thay bốn tích hợp bắt buộc Day 2. Fixture có secret canary trong filename/content/labels; smoke kiểm tra canary không xuất hiện trong phản hồi.

| Đường client đã chạy | Protocol trên wire |
|---|---|
| SDK client 2.0.0, pin modern | 2026-07-28 |
| SDK client 2.0.0, auto | 2026-07-28 |
| SDK client 2.0.0, legacy | 2025-11-25 |
| SDK 1.30.0, client legacy thật | 2025-11-25 |

Modern dùng `server/discover`; legacy dùng `initialize` và `notifications/initialized`. Tất cả gọi `tools/list`, `tools/call`. SDK v2 probe stdio bằng một process phụ; smoke gọi thêm `server/discover` qua process chính để ghi nhận RPC trực tiếp. Smoke không giả định mọi Claude/Codex/Antigravity build đã dùng protocol mới.

## Tool và quyền thực thi

| Tool | Input | Output |
|---|---|---|
| `insighthub_health` | `{}` | `live`, `ready`, `databaseReady`: boolean |
| `insighthub_list_documents` | `{"limit":2}`, mặc định 10, từ 1 đến 20 | `documents: [{id,status,chunk_count}]`, `returned`, `truncated` |
| `prometheus_summary`, opt-in | `{"query":"requests_5m"}`, hoặc `errors_5m`, `documents` | Query ID, giá trị aggregate hoặc null, cửa sổ `5m`/`instant` |

Tool bị loại khỏi allowlist không được đăng ký và vẫn bị chặn khi gọi thẳng `tools/call`. Service kiểm tra quyền thêm lần nữa. Chuỗi rỗng là deny all, tên không hợp lệ làm startup fail. `readOnlyHint` chỉ là mô tả; quyền do code server thực thi.

Không có tool đọc file, nội dung tài liệu, chat, upload, delete, exec, shell, kubectl, Docker socket hoặc URL tùy ý. Không nhận credential. Projection bỏ filename, created_at, content, nhãn metric và dữ liệu lỗi upstream, không dựa vào regex đoán secret. Lỗi SDK được lọc để tránh phản chiếu input vào message/content; JSON-RPC request ID vẫn phải được echo theo giao thức.

## Cấu hình

| Biến môi trường | Mặc định | Giới hạn |
|---|---|---|
| `INSIGHTHUB_API_URL` | `http://127.0.0.1:8000` | Origin loopback, không path/query/userinfo |
| `INSIGHTHUB_MCP_TOOLS` | `insighthub_health,insighthub_list_documents` | CSV tên tool chính xác; rỗng là deny all |
| `INSIGHTHUB_MCP_PROMETHEUS` | `0` | Chỉ `0` hoặc `1` |
| `INSIGHTHUB_PROMETHEUS_URL` | `http://127.0.0.1:9090` khi bật | Origin loopback |
| `INSIGHTHUB_MCP_TIMEOUT_MS` | `1500` | Số nguyên 1-5000, deadline tuyệt đối cho mỗi HTTP request |
| `INSIGHTHUB_MCP_MAX_BYTES` | `65536` | Số nguyên 1-262144 cho mỗi response |

Chấp nhận `127.0.0.1`, `[::1]`, hoặc `localhost` được đổi thành `127.0.0.1` trước khi kết nối. Không DNS resolution, proxy môi trường, redirect, cookie hoặc retry. Chỉ HTTP nội bộ, GET cố định, header tối đa 8192 bytes, từ chối compressed/non-JSON body. Tối đa 4 tool calls đồng thời; health có 2 GET đồng thời. Buffer stdio tối đa 65536 bytes. Server không mở HTTP listener.

```sh
# POSIX shell: bật Prometheus cho server, sau khi Prometheus đã chạy.
INSIGHTHUB_MCP_PROMETHEUS=1 \
INSIGHTHUB_MCP_TOOLS=insighthub_health,insighthub_list_documents,prometheus_summary \
node tools/mcp/src/server.mjs
```

Có thể đặt cùng các biến trong `env` của host trên Windows. Để kiểm chứng live cả Prometheus, dùng cùng env với `node tools/mcp/smoke.mjs --live`.

Ba query được cố định trong [core.mjs](src/core.mjs): tổng request tăng trong 5 phút, tổng HTTP 5xx tăng trong 5 phút, tổng document gauge tại thời điểm hiện tại. Prometheus nhận `timeout=1s`; không nhận PromQL, khoảng thời gian, label hoặc URL do model gửi. Kết quả tối đa một sample, loại bỏ toàn bộ labels. Không có series trả null, không kết luận là 0. Prometheus phải scrape đúng môi trường InsightHub; nhiều scrape trùng có thể cộng trùng. Đây là tín hiệu kiểm tra, chưa đủ để kết luận SLO/RCA.

## Chọn một host: Claude Code, ChatGPT-Codex hoặc Antigravity

- [.mcp.json.template](../../.mcp.json.template) là template **Claude project**, đường dẫn tương đối yêu cầu launch Claude Code từ repo root. Template chưa tự kích hoạt và không chứa trường placeholder giả.
- Desktop/GUI hoặc host có cwd khác: chạy lệnh dưới để tạo config với đường dẫn Node và server tuyệt đối, xử lý cả dấu cách/Unicode. Helper chỉ in stdout, không sửa file hoặc cấu hình host.
- Claude Desktop nhận nội dung `mcpServers` trong cấu hình Desktop; không mặc định đọc file project của Claude Code.
- Antigravity: dùng mode antigravity, ghép mcpServers vào config mà UI của build đang dùng; [host guide](../../docs/Guide_Coding_Host_DO2603.md) có đường dẫn, context rule và evidence. Không mặc định đọc .mcp.json.
- Codex dùng TOML `mcp_servers`, không nạp trực tiếp JSON template. Ghép block sinh ra vào config được chọn của Codex. `enabled_tools` bổ sung bộ lọc host; `INSIGHTHUB_MCP_TOOLS` vẫn là quyền server.

```sh
node tools/mcp/host-config.mjs claude
node tools/mcp/host-config.mjs codex
node tools/mcp/host-config.mjs antigravity
```

Mỗi máy tự sinh đường dẫn. Không commit output có đường dẫn riêng của máy vào template dùng chung. Chỉ cài dependency lúc chuẩn bị; host launch `node` trực tiếp, không `npx ...@latest` tải package mỗi phiên.

## Ranh giới và chẩn đoán

- Baseline API: `api/app/routers/health.py`, `documents.py`, `core/metrics.py` được đọc ngày 08/09/2026. `GET /documents` ở baseline lấy toàn bộ metadata, không có pagination; server này cắt output nhưng không thể giảm truy vấn DB phía API. Response vượt byte cap sẽ fail, không trả kết quả giả.
- Read-only nghĩa là không sửa dữ liệu nghiệp vụ. GET vẫn có thể tăng request counter và refresh gauge như API hiện có.
- Đây là process tin cậy do người dùng launch. Env là cấu hình operator, không phải tham số LLM; host có quyền sửa source/env vẫn thay đổi được policy. Loopback không xác thực danh tính service; dùng riêng môi trường lab, không port-forward production có dữ liệu nhạy cảm.
- Không đưa công cụ đọc metadata này lên HTTP/public hoặc thêm cloud credentials. Nhu cầu remote phải được thiết kế riêng.
- `MCP_STARTUP_REJECTED`: kiểm tra URL, tên tool, flag và giới hạn env.
- `READ_ONLY_REQUEST_FAILED`: kiểm tra API readiness, schema và kích thước response qua workflow local. Không tăng byte cap hoặc timeout vượt hard cap; không bật output lỗi thô.
- Bind `EPERM` khi chạy test/smoke: chạy trong môi trường cho phép loopback fixture. Đây không phải bằng chứng MCP protocol thất bại.
- `tools/list` có tool nhưng gọi bị từ chối: kiểm tra input schema và cả hai lớp allowlist; không tự cấp quyền ghi.

## Kiểm chứng và cập nhật

`test/core.test.mjs` kiểm tra allowlist, SSRF/redirect, strict input, response projection, body/time limit, cancellation và concurrency. `test/server.test.mjs` dùng SDK client gửi request thật để kiểm tra tool disabled, shell/delete/file bị từ chối, argument vượt giới hạn và lỗi không lộ canary.

`package-lock.json` khóa dependency tree và integrity; SDK client v1 chỉ là devDependency để đối chiếu. Chạy tests và smoke từ lockfile, lưu protocol/backend thật trong evidence. Fixture không thay kiểm chứng API live hoặc tool call qua host/model. Research snapshot và nhật ký kiểm thử của mentor được giữ ngoài starter.