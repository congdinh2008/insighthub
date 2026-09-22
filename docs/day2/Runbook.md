# Day 02 - Reproduce and operate

## Prerequisites

Bản đã kiểm thử: macOS arm64, Docker Desktop 4.89.0 (engine 29.7.2, MCP Gateway 0.43.3), Node 24.16.0, Python 3.12 cho quality tools, kubectl 1.36.1 và Codex CLI 0.154.0 đã đăng nhập. Trên macOS, cài `socat` bằng `brew install socat` để Docker MCP Gateway kết nối server container. Installer binary hỗ trợ thêm Linux/amd64 nhưng Docker networking chưa được E2E ngoài Docker Desktop. Không dùng cluster/database của lớp khác. Chạy từ root repo; đường dẫn có dấu cách được hỗ trợ.

Lab dùng các giá trị cố định trong `.env.example`: project `insighthub-day2-lab`, API 18002, web 13002, Prometheus 19092, Docker read proxy 23752. Launcher/test harness dùng cùng các giá trị này; không chỉ đổi port trong Compose mà quên config MCP. Nếu cổng đã bận, kiểm tra process sở hữu rồi điều chỉnh đồng bộ hoặc dừng lab của chính mình.

## Dựng lab

```bash
export COMPOSE_PROJECT_NAME=insighthub-day2-lab
export API_PORT=18002 WEB_PORT=13002 PROMETHEUS_PORT=19092
export RAG_MODE=fixture LLM_PROVIDER=fixture EMBEDDING_PROVIDER=fixture
npm ci --prefix tools/mcp --ignore-scripts
npm ci --prefix tools/mcp/day2 --ignore-scripts
python3 tools/mcp/day2/install.py

docker compose --env-file tools/mcp/day2/.env.example \
  -f docker-compose.yml -f docker-compose.day2.yml up --build -d --wait

tmp/day2/bin/kind create cluster --name insighthub-day2 \
  --config tools/mcp/day2/lab/kind.yml --kubeconfig tmp/day2/admin.kubeconfig
python3 tools/mcp/day2/configure.py
```

Nếu cluster đã tồn tại, dùng kubeconfig riêng đã tạo và chạy lại configure; không tạo cluster thứ hai. `configure.py` áp RBAC/sample pod idempotently, tạo SA token hạn 6h, tái tạo source snapshot, cài Docker MCP profile `insighthub-dev` cùng hai project catalogs, sinh launch definitions và cài năm MCP vào config project của Codex, Claude Code và Antigravity IDE. Các cấu hình khác được giữ nguyên; không sửa config host global. Catalogs nằm tại `~/.docker/mcp/catalogs/insighthub-filesystem.json` và `~/.docker/mcp/catalogs/insighthub-operations.json`. Config/server launch không chứa token; token nằm trong `tmp/day2/readonly.kubeconfig` permission 0600, thư mục state 0700. Admin kubeconfig chỉ operator dùng.

`tmp/day2/source-view` là bản source sạch được expose dưới `/project`; không include runtime secrets/ignored files/evidence hoặc symlink nguồn. Configure chỉ được chạy khi các Filesystem clients đã ngắt kết nối để tránh giữ mount snapshot cũ. Sau sửa source, chạy lại configure và reconnect. Đừng mở file token trong Inspector hoặc đưa vào screenshot.

Kiểm tra baseline:

```bash
docker compose config --services
kubectl --kubeconfig tmp/day2/admin.kubeconfig get sa mcp-readonly -n insighthub
kubectl --kubeconfig tmp/day2/admin.kubeconfig get clusterrole mcp-readonly -o yaml
kubectl --kubeconfig tmp/day2/readonly.kubeconfig auth can-i get pods -n insighthub
kubectl --kubeconfig tmp/day2/readonly.kubeconfig auth can-i delete pods -n insighthub
```

Base Compose phải có đúng `web/api/postgres/redis/ingestion-worker`. SA get pods: yes; delete pods: no. Override chỉ thêm dependencies MCP local, chưa triển khai application lên Kubernetes.

## Tạo incident và chạy acceptance

```bash
DAY2_REQUIRED_VALUE= docker compose --env-file tools/mcp/day2/.env.example \
  -f docker-compose.yml -f docker-compose.day2.yml --profile day2-debug \
  up -d --force-recreate debug-case

make test-day2 PYTHON=.venv/bin/python
make test-day2-live PYTHON=python3
```

Unit tests không cần cluster. Live check gọi thật năm server, kiểm output positive/negative, RBAC bằng token SA, API proxy denial và HTTP/PromQL cùng timestamp. Harness host đọc `tmp/day2/servers.json`, áp từng field config bằng CLI `-c` tương ứng với `codex.config.toml`, dùng model mặc định của host và thu event JSONL/timestamp. Nó dùng approval chuẩn `--approve-for-me`, tắt shell/apps/multi-agent; không dùng bypass. Không coi exit code của process model là đủ: harness kiểm actual completed MCP calls trên từng server. Raw stderr chỉ lưu local vì có thể chứa thông tin môi trường.

Artifacts local: `probe-all.json`, `live-check.json`, `host-trace.json`, `host-summary.md` trong `tmp/day2`. Parse đối chiếu config:

```bash
python3 - <<'PY'
import json, tomllib
from pathlib import Path
state = Path('tmp/day2')
assert tomllib.loads((state/'codex.config.toml').read_text())['mcp_servers'] == json.loads((state/'servers.json').read_text())
print('Host configuration matches generated launch definitions')
PY
```

## Config project cho ba host

`configure.py` sinh các file dưới đây từ cùng launch definitions với năm server IDs: `filesystem`, `docker-operations`, `kubernetes`, `prometheus`, `insighthub`. Học viên chọn một host để thực hành; runtime acceptance của solution dùng Codex.

| Host | File local trong root repo | Template portable trong `tools/mcp/day2/` |
|---|---|---|
| Codex Desktop/CLI | `.codex/config.toml` | `codex.config.toml.template` |
| Claude Code | `.mcp.json` | `claude.mcp.json.template` |
| Antigravity IDE | `.agents/mcp_config.json` | `antigravity.mcp_config.json.template` |

Templates dùng placeholder; không copy nguyên để chạy. Config thực chứa executable/path đã resolve cho máy, được Git-ignore và permission 0600; credentials nằm trong state riêng. Chạy setup ở trên để sinh lại trên máy học viên. Khi đã có launch definitions và chỉ cần cài lại config project:

```bash
python3 tools/mcp/day2/configure.py --project-config-only
python3 scripts/check-agent-setup.py --host codex --config .codex/config.toml
python3 scripts/check-agent-setup.py --host claude --config .mcp.json
python3 scripts/check-agent-setup.py --host antigravity --config .agents/mcp_config.json
```

Generator giữ settings/server khác. Codex dùng block Day 02 riêng; JSON được merge theo tên server. Nếu JSON đã có entry MCP do generator quản lý khác nội dung sinh ra, setup dừng trước khi ghi cả ba config. Review khác biệt, sao lưu phần tùy chỉnh và chỉ xóa entry Day 02 cần sinh lại rồi chạy setup; không xóa config khác.

- **Codex:** mở repo `insighthub` trong workspace đã trusted, bắt đầu phiên mới và chạy `codex mcp list --json`; review `enabled_tools` theo [OpenAI Docs](https://learn.chatgpt.com/docs/extend/mcp#connect-codex-to-an-mcp-server).
- **Claude Code:** chạy `claude` từ repo, chấp nhận workspace trust/project MCP khi host yêu cầu, kiểm `/mcp`; `claude mcp get filesystem` kiểm scope/config. `.mcp.json` là project config của Claude Code, theo [Claude Code Docs](https://code.claude.com/docs/en/mcp#project-scope).
- **Antigravity IDE:** mở repo, vào **MCP Servers > Manage MCP Servers > View raw config**, xác nhận workspace `.agents/mcp_config.json`, refresh server list và review tools. Vị trí workspace và JSON schema theo [Google Antigravity Docs](https://antigravity.google/docs/ide/mcp). Nếu build đang mở config global, chọn workspace config thay vì ghi đè config global.

Codex hỗ trợ `enabled_tools`; JSON của hai host còn lại chỉ chứa fields transport được hỗ trợ (`command`, `args`, `env`; Claude thêm `type: stdio`). Review quyền/tool selection ở host đã chọn. Read-only vẫn được enforce bằng filesystem mount, Docker proxy, Kubernetes RBAC và cấu hình backend. Filesystem Gateway dùng tập server cố định nên không expose Dynamic MCP management tools. Không coi tool visibility giữa các host là authorization boundary.

Static checker chỉ xác nhận context/config shape. Config discovery không chứng minh backend đang Connected: khởi động lab và refresh SA token trước khi gọi tools. Khi nghiệm thu bằng Claude/Antigravity, thực hiện cùng các read/deny cases và thu host trace mới. `host_check.py` chỉ hỗ trợ Codex.

Runtime source hashes và kết quả chạy nằm trong `manifest.json` cùng các runtime reports. Mọi evidence phải được tạo từ đúng generated config của branch hiện tại, không thay bằng kết quả parse hoặc discovery.

## MCP Inspector bằng Computer Use / Control Browser

```bash
MCP_AUTO_OPEN_ENABLED=false HOST=127.0.0.1 CLIENT_PORT=6274 SERVER_PORT=6277 \
  node tools/mcp/day2/node_modules/@modelcontextprotocol/inspector/clients/launcher/build/index.js \
  --web --config tmp/day2/inspector.json --server filesystem
```

Mở URL local do Inspector in ra; giữ authentication mặc định, không chia sẻ token/URL có token. Chọn server, Connect, Tools, nhập args và Execute Tool. Sau mỗi server Disconnect để chuyển server khác.

| Server | Tool/args | Expected |
|---|---|---|
| Filesystem | `read_file` với path `/project/README.md` | Tiêu đề InsightHub |
| Docker | `get_diagnostic_logs` với `{}` | `DAY2_CONFIG_MISSING` trước sửa, `DAY2_CONFIG_OK` sau sửa |
| Kubernetes | `pods_list_in_namespace`, namespace `insighthub` | `mcp-sample`, Running/1/1 |
| Prometheus | `query`, query `up{job=~"insighthub-(api\|worker)"}` (không escape dấu pipe trong form) | Hai series = 1 |
| InsightHub | `insighthub_health` với `{}` | Ba boolean true |

Negative: Filesystem path `/outside-project-canary.txt` phải denied; Kubernetes namespace `kube-system` phải forbidden bằng `system:serviceaccount:insighthub:mcp-readonly`. Protocol OK chỉ là JSON-RPC transport thành công, cần đọc `isError`/Tool Error để đánh giá denial. Lưu screenshot cả kết quả và server/tool identity.

Mở web `http://127.0.0.1:13002`, dùng picker upload `sample-docs/so-tay-van-hanh.md`, chờ ready/chunks, chat và kiểm nguồn. Đây là application fixture mode, không phải đánh giá chất lượng model RAG. Mở Prometheus `http://127.0.0.1:19092`, query `up` và đối chiếu hai job. Backend MCP vẫn live, tách biệt RAG fixture.

## RCA và phục hồi

Host chẩn đoán read-only, operator sửa đúng service lab:

```bash
python3 tools/mcp/day2/host_check.py --debug-only
DAY2_REQUIRED_VALUE=configured docker compose --env-file tools/mcp/day2/.env.example \
  -f docker-compose.yml -f docker-compose.day2.yml --profile day2-debug \
  up -d --force-recreate debug-case
python3 tools/mcp/day2/host_check.py --debug-only --recovery
make test-day2-host PYTHON=python3
```

`--debug-only` chứng minh host chẩn đoán incident thật. `--recovery` chứng minh remediation. `make test-day2-host` là acceptance cuối trên trạng thái healthy và gọi đủ năm server. Restart không nạp env mới; recreate là thao tác operator. Kiểm log OK và trạng thái running qua MCP. Reload web sau recovery, tài liệu vẫn ready. Ghi case theo `debug-session-day2.md`; kết quả thời gian của máy khác phải tự đo.

## Regression và lỗi kết nối

```bash
make test-image test-backend test-worker COMPOSE_PROJECT_NAME=insighthub-day2-lab
make test-day1 API_URL=http://127.0.0.1:18002 WEB_URL=http://127.0.0.1:13002 PYTHON=.venv/bin/python
make lint typecheck test-verifiers PYTHON=.venv/bin/python
make test-mcp
INSIGHTHUB_API_URL=http://127.0.0.1:18002 node tools/mcp/smoke.mjs --live
PATH="$PWD/.venv/bin:$PATH" pre-commit run --all-files
```

| Triệu chứng | Kiểm tra/sửa trong lab |
|---|---|
| Executable not found | Chạy install, kiểm checksum và đường dẫn tuyệt đối generator; không dùng shell string chứa path có space |
| K8s unauthorized sau 6h | Re-run configure để refresh token rồi reconnect; không chuyển sang admin credential |
| K8s forbidden namespace khác | Expected denial; dùng `insighthub`, không mở ClusterRoleBinding |
| Prometheus MCP connection closed, bind 8080 | Launcher phải có `--web.listen-address=127.0.0.1:0`; tránh xung đột host/Inspector |
| Gateway tool bị approval trong noninteractive host | Dùng luồng approval chuẩn/harness; không bypass hoặc gắn annotation giả để né policy |
| Docker logs không có dữ liệu | Đã khởi tạo debug profile đúng project chưa; proxy chỉ cho đọc hai target đã định nghĩa |
| Filesystem source chưa cập nhật | Disconnect, configure, reconnect; snapshot không phải live mount toàn bộ repo |
| Filesystem chỉ hiện Dynamic MCP tools | Dùng launcher project với `--servers=filesystem`; không chạy profile trực tiếp trong phiên nghiệm thu |

## Dừng lab

Dừng Inspector bằng Ctrl+C và đóng host session trước. Các lệnh dưới chỉ nhắm lab này, giữ Docker volumes:

```bash
docker compose --env-file tools/mcp/day2/.env.example \
  -f docker-compose.yml -f docker-compose.day2.yml --profile day2-debug down
tmp/day2/bin/kind delete cluster --name insighthub-day2
```

Không dùng Docker prune hoặc xóa volumes chung. Sau khi xóa cluster, kubeconfig/token local cũ không còn sử dụng được; lần chạy sau tạo lại cluster/config. Profile và catalogs riêng có thể giữ để tái lập; chúng không chứa credential.
