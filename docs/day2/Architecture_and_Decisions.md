# Day 02 - Kiến trúc và quyết định

## Backend được chọn

| Backend | Upstream và pin | Lý do chọn |
|---|---|---|
| Filesystem | [MCP reference servers](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem), Docker signed image `mcp/filesystem@sha256:35fc...3f67` | Reference implementation được Docker MCP Catalog phân phối; chạy container cô lập qua Docker MCP Gateway |
| Docker/container | [Docker MCP Gateway](https://github.com/docker/mcp-gateway/releases/tag/v0.43.3) `0.43.3` + catalog POCI project tùy chỉnh + Docker CLI `29.7.2` digest | Gateway/CLI chính chủ; ba tools và proxy do project định nghĩa để giới hạn quyền đọc |
| Kubernetes | [containers/kubernetes-mcp-server](https://github.com/containers/kubernetes-mcp-server/releases/tag/v0.0.66) `0.0.66` | Upstream của hệ sinh thái containers, có maintenance/tool filtering/read-only. Không gán nhãn Kubernetes/CNCF official |
| Prometheus | [prometheus/prometheus-mcp](https://github.com/prometheus/prometheus-mcp/releases/tag/v0.18.0) `0.18.0` | Server do tổ chức Prometheus duy trì; query trực tiếp backend local |
| InsightHub | `tools/mcp` version `1.0.0`, SDK `2.0.0` lockfile hiện có | Tái sử dụng health và metadata tài liệu, phù hợp observability/ChatOps ở các day sau |

Review upstream kiểm tra repository maintainer, release artifact, checksum, schema, permission model và khả năng chạy live trong lab. Prometheus MCP do tổ chức Prometheus duy trì; Filesystem là MCP reference server; Docker Gateway và Registry do Docker duy trì. Kubernetes MCP thuộc dự án `containers`, không gắn nhãn Kubernetes/CNCF official. Gateway `0.43.3` là **prerelease** đã khóa checksum và kiểm thử cho lab, không tuyên bố production certification.

Mapping machine-readable: `tools/mcp/day2/backends.json`. Binary URLs/checksums: `tools/mcp/day2/artifacts.lock.json`. npm: hai `package-lock.json` trong `tools/mcp` và `tools/mcp/day2`. Images: digest trong Toolkit definition, Dockerfile, Compose override và kind config. InsightHub dùng source cùng branch và lockfile hiện có. Không tải `latest` khi host khởi chạy.

Không tạo thêm custom FastMCP trùng hai tool nội bộ. Việc tái sử dụng server thứ năm không thay tiêu chí Should-have AWS hoặc bonus custom FastMCP. Chưa triển khai chức năng Day 03-06.

## Tên và nguồn MCP

Server IDs ổn định theo chức năng: `filesystem`, `docker-operations`, `kubernetes`, `prometheus`, `insighthub`. Tên host entry không phụ thuộc ngày học; đường dẫn tài liệu/evidence theo Day 02 chỉ tổ chức bài tập. `docker-operations` có ba tools `list_containers`, `get_diagnostic_logs`, `get_worker_logs`; hai log tools đọc target cố định của lab, không nhận container tùy ý.

Filesystem và Prometheus dùng implementation chính chủ upstream. Kubernetes dùng `containers/kubernetes-mcp-server`, không gắn nhãn Kubernetes/CNCF official. InsightHub là server nội bộ từ starter. Gateway Docker chính chủ không làm catalog/tool project trở thành upstream official. Profile `insighthub-dev` và hai project catalogs quản lý Filesystem cùng Docker operations. Xem [Docker MCP Toolkit](Docker_MCP_Toolkit.md) để hiểu cách profile, catalog và Gateway được áp dụng.

## Topology và quyền

```text
Codex host / MCP Inspector
  |-- stdio -> Docker MCP Gateway -> Filesystem upstream -> /project (snapshot read-only)
  |-- stdio -> Docker Gateway -> pinned Docker CLI -> lab read proxy -> Docker Engine
  |-- stdio -> Kubernetes upstream -> kubeconfig mcp-readonly -> kind / insighthub
  |-- stdio -> Prometheus upstream -> 127.0.0.1:19092 -> API/worker metrics
  `-- stdio -> InsightHub MCP -> 127.0.0.1:18002 -> health / document metadata
```

Host tạo client/session riêng cho từng server. Inspector dùng cùng launcher/backend, nhưng không thay bằng chứng model gọi tool trong host. SDK probe là kiểm tra giao thức độc lập. Giao thức được ghi từ handshake thực tế, không suy từ version SDK. Inspector đàm phán revision legacy `2025-11-25`; SDK auto có thể đàm phán modern `2026-07-28` với Kubernetes/InsightHub.

Tất cả MCP dùng stdio local: không cần public MCP HTTP endpoint/auth server. Streamable HTTP phù hợp server dùng chung/remote nhưng phải có xác thực, TLS và quyền theo caller; bài này chưa cần. Prometheus MCP có telemetry HTTP riêng: bind `127.0.0.1:0` để không expose toàn mạng hoặc xung đột khi hai client chạy. Inspector giữ authentication mặc định, listen loopback.

## Threat model ngắn

| Backend / tài sản | Threat | Enforcement và giới hạn | Test |
|---|---|---|---|
| Filesystem / source | Traversal, ghi file, đọc credential | Docker Gateway xác minh signed image; network disabled; chỉ mount snapshot sạch `/project` ở chế độ read-only. Snapshot loại Git internals, ignored files, runtime evidence, secret `.env` và symlinks nguồn. Gateway chỉ expose ba tool đọc | Đọc README; outside/traversal denied; `write_file` không được discover/call; canary không đổi |
| Docker / daemon | Model gửi shell/argv/mutation, liệt kê lab khác, dump Env | Ba POCI commands cố định, không nhận args. MCP tool container không có socket. Proxy GET allowlist, project filter bắt buộc, hai log targets, inspect projection không Env/Mounts/Labels. Tail 100, 128 KiB, timeout 3s, concurrency 4 | Tool mutation unknown; HTTP mutation/out-of-scope 403; caller filters không mở rộng scope; inspect canary không lộ Env |
| Kubernetes / cluster | Quá quyền, đọc secrets, exec hoặc đổi namespace | SA `mcp-readonly`, token 6h/0600; một context; ClusterRole chỉ read verbs; RoleBinding chỉ `insighthub`; upstream read-only/disable-multi-cluster/4 tools | get/list được; delete/create/patch/exec/secrets/kube-system không được bằng chính token SA |
| Prometheus / metrics | Admin mutation, query endpoint khác, query lớn | URL cố định; không bật admin/lifecycle backend hoặc dangerous MCP tools. Host chỉ query/range_query/list_targets; timeout 5s. Truncation 20 là default vận hành, caller có thể đổi, không là hard cap | Samples API/worker thật; empty khác zero; query cùng timestamp khớp HTTP; admin/URL override denied |
| InsightHub / API | Ghi dữ liệu, nội dung tài liệu thành prompt injection | Hai tool read-only hiện có, schema strict/output bounded; metadata không nội dung tài liệu; endpoint loopback | Health thật, documents metadata; regression starter SDK và permission tests |

Docker proxy là helper quyền nhỏ cho lab, **không phải MCP implementation mới**. Chỉ proxy giữ socket: `:ro` trên socket không làm Docker Engine read-only; nếu proxy bị chiếm thì socket vẫn là ranh giới nhạy cảm. Trust boundary gồm mã proxy và máy operator. Loopback không phải xác thực đa người dùng; solution chỉ chứng nhận lab local của một học viên. Docker Desktop macOS arm64 đã E2E; binary installer hỗ trợ macOS/Linux arm64/amd64 nhưng chưa chứng nhận Docker networking trên Linux. `host.docker.internal` là prerequisite Docker Desktop của topology đã test.

Filesystem Roots là đề xuất của client, không phải authorization boundary. Host thực tế được cô lập bởi container chỉ mount snapshot `/project` ở chế độ read-only và tắt network. Snapshot được tạo lại khi chạy configure, nên đọc source sau thay đổi cần refresh config/snapshot rồi reconnect.

Codex có `enabled_tools` để giảm bề mặt model, không thay authorization backend. Gateway POCI thiếu `readOnlyHint`; dùng approval chuẩn của host (harness: `--approve-for-me`), không bypass. Annotation chỉ là metadata. MCP output/log/document là dữ liệu chưa tin cậy, không cấp quyền hay chỉ dẫn cho agent.
