# Docker MCP Toolkit trong InsightHub

Solution dùng Docker Desktop 4.89.0 và Docker MCP Gateway v0.43.3. Toolkit hiện ở trạng thái Beta, Profiles ở trạng thái Early Access. Cấu hình Day 02 dùng các thành phần Toolkit theo phạm vi có thể kiểm soát và kiểm thử được. [Docker MCP Toolkit](https://docs.docker.com/ai/mcp-catalog-and-toolkit/toolkit/), [MCP Profiles](https://docs.docker.com/ai/mcp-catalog-and-toolkit/profiles/).

## Thiết kế được triển khai

| Thành phần | Tên | Vai trò |
|---|---|---|
| Profile | `insighthub-dev` | Lưu Filesystem server, image digest, mount read-only, network policy và tool allowlist |
| Catalog | `insighthub-filesystem` | Chạy Filesystem qua Gateway với tập server cố định |
| Catalog | `insighthub-operations` | Cung cấp ba POCI Docker commands cố định qua policy proxy |
| Gateway | `docker-mcp` v0.43.3 | Xác minh image, tạo container cô lập và expose stdio MCP |
| Host configs | Codex, Claude Code, Antigravity | Khởi chạy năm MCP entries của project bằng cùng generated definitions |

```mermaid
flowchart LR
    Hosts[Codex / Claude Code / Antigravity] --> FS[filesystem entry]
    Hosts --> Ops[docker-operations entry]
    FS --> GW1[Docker MCP Gateway]
    Ops --> GW2[Docker MCP Gateway]
    Profile[Profile: insighthub-dev] -. quản lý policy .-> GW1
    GW1 --> FSServer[Signed Filesystem image]
    FSServer --> Snapshot[/project read-only snapshot]
    GW2 --> POCI[Three constant Docker commands]
    POCI --> Proxy[Read-only Docker API proxy]
```

Filesystem dùng `--servers=filesystem` cùng catalog project khi host khởi chạy. Chế độ này giữ tập server cố định và Docker Gateway tự tắt Dynamic MCP management tools. Profile `insighthub-dev` vẫn là nguồn quản lý có thể xem trong Docker Desktop hoặc bằng CLI. Không chạy profile trực tiếp trong phiên nghiệm thu vì Dynamic MCP được bật mặc định ở cấp Docker Desktop và sẽ expose các management tools ngoài phạm vi Day 02. [Dynamic MCP](https://docs.docker.com/ai/mcp-catalog-and-toolkit/dynamic-mcp/).

Docker operations dùng POCI project catalog ngoài profile. Profile schema của Gateway v0.43.3 nhận `server`, `remote` và image references nhưng không nhận POCI local entry theo cách giữ ba command policy của project. Catalog riêng vì vậy là boundary phù hợp cho container diagnostics. Catalog `docker` có sẵn trong Docker MCP Catalog nhận Docker CLI arguments linh hoạt và truy cập Docker socket, rộng hơn quyền read-only của bài này. [Server entry specification](https://github.com/docker/mcp-gateway/blob/main/docs/server-entry-spec.md), [Docker catalog entry](https://github.com/docker/mcp-registry/blob/main/servers/docker/server.yaml).

## Nguồn và provenance

| Backend | Nguồn | Quyết định |
|---|---|---|
| Filesystem | MCP reference server, signed image trong Docker MCP Catalog | Dùng image digest cố định, mount `/project:ro`, network disabled, chỉ `read_file`, `list_directory`, `list_allowed_directories` |
| Docker/container | Docker MCP Gateway chính chủ | Dùng POCI custom vì tools là policy riêng của InsightHub; không mô tả chúng là Docker official tools |
| Kubernetes | `containers/kubernetes-mcp-server` | Giữ upstream đã review và pin; không thay ngầm bằng catalog entry `Flux159/mcp-server-kubernetes` |
| Prometheus | `prometheus/prometheus-mcp` | Giữ upstream do tổ chức Prometheus duy trì; không thay bằng catalog entry `pab1it0/prometheus-mcp-server` |
| InsightHub | MCP nội bộ của starter | Chỉ health và document metadata, không thay bốn backend bắt buộc |

Docker build, sign hoặc phân phối image không làm tác giả server trở thành Docker. `backends.json` ghi riêng upstream, artifact và permission profile để tránh gắn nhãn official sai. [Docker MCP Catalog](https://docs.docker.com/ai/mcp-catalog-and-toolkit/catalog/).

## Cài đặt và kiểm tra profile

`configure.py` tạo snapshot trước, cài catalog/profile an toàn rồi sinh config host:

```bash
python3 tools/mcp/day2/configure.py
docker mcp profile show insighthub-dev --format json
```

Profile phải có đúng một server `filesystem` với:

- image `mcp/filesystem@sha256:35fcf0217ca0d5bf7b0a5bd68fb3b89e08174676c0e0b4f431604512cf7b3f67`
- volume `<repo>/tmp/day2/source-view:/project:ro`
- `disableNetwork: true`
- tool allowlist gồm `read_file`, `list_directory`, `list_allowed_directories`

Installer không sửa profile hoặc catalog khác. Nếu `insighthub-dev` tồn tại nhưng khác contract, installer dừng để operator review. Trên macOS, Docker MCP Gateway v0.43.3 cần `socat` trong `PATH`.

## Quyền và vận hành

`MCP_GATEWAY_DOCKER_BIND_ALLOWED_PATHS` chỉ cấp đúng source snapshot cho read-only bind. Không dùng `MCP_GATEWAY_DOCKER_BIND_ALLOW_WRITABLE_PATHS`. Gateway giữ signature verification mặc định, `block-secrets` mặc định và không nhận toàn bộ environment của terminal. [Gateway security](https://github.com/docker/mcp-gateway/blob/main/docs/security.md).

Tool visibility là lớp giảm bề mặt. Authorization cuối vẫn nằm ở read-only mount, Docker API proxy và Kubernetes RBAC. Test bắt buộc gồm discovery allowlist, read thành công, outside/traversal denial, Docker mutation denial và Kubernetes forbidden cases.

Credentials do backend hoặc Docker Desktop credential store quản lý. Không commit token, kubeconfig hoặc profile database. Profile export chỉ phù hợp sau khi làm sạch đường dẫn máy và kiểm tra không chứa credential. [Docker MCP CLI](https://docs.docker.com/ai/mcp-catalog-and-toolkit/cli/).

## Mở rộng sau Day 02

Khi một giai đoạn sau cần thêm MCP, ưu tiên catalog entry có upstream rõ, image digest, quyền tối thiểu và use case cụ thể. AWS MCP chỉ thêm khi có IAM/SSO profile `mcp-readonly` và test đúng account/role. Terraform MCP chỉ thêm ở Day 03 sau khi định nghĩa rõ quyền đọc plan/state. Không thêm server chỉ để tăng số lượng.
