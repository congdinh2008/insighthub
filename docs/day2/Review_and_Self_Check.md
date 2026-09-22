# Day 02 - Review và self-check

## Requirement mapping

| ID | Kết quả | Bằng chứng |
|---|---|---|
| MH1 config theo host | PASS | Ba config project parse hợp lệ; `host-config-check.json` ghi server IDs và tools hiện tại. Codex có runtime calls trong `host-trace.json`; Claude/Antigravity có cùng generated definitions và static config check |
| MH2 >=4 backend | PASS | Filesystem, Docker, Kubernetes, Prometheus độc lập; InsightHub bổ sung, xem Architecture |
| MH3 host connected + live call | PASS | [Host trace](../evidence/day2/host-trace.json), 6 tool calls trên 5 server thành công |
| MH4 version pin | PASS | `artifacts.lock.json`, npm locks, Docker image digests, source/image hashes trong evidence manifest |
| MH5 ServiceAccount | PASS | `infra/k8s/mcp-readonly/rbac.yml`, SA `insighthub:mcp-readonly` và live SA auth checks |
| MH6 ClusterRole read-only | PASS | Chỉ get/list/watch; RoleBinding namespace; `live-check.json` có 9 permission checks |
| MH7 Filesystem project root | PASS | `/project` là snapshot sạch duy nhất; outside/traversal denied; write tool không được expose; mount `:ro` và canary không đổi |
| MH8 Inspector | PASS | Năm screenshot tool invocation thật qua Computer Use; thêm FS/K8s denial |
| MH9 debug session | PASS | [Crashing container case](../../debug-session-day2.md), RCA và recovery qua host MCP |
| MH10 quiz >=7/10 | PENDING | Chưa có quiz form chính thức; [bộ luyện tập](Quiz_and_Answers.md) không thay điểm lớp |
| SH namespace/context, K8s read-only, env template | PASS | Kubeconfig một context/namespace, launcher flags, `.env.example` |
| SH AWS MCP / NH Terraform MCP | Không chọn | Ngoài phạm vi lab local; không cần tài nguyên AWS cho Day 02 này |
| NH custom FastMCP | Không nhận bonus | Tái sử dụng server InsightHub hiện có; không tự viết MCP mới |
| NH threat model | PASS | [Bảng quyền và giới hạn](Architecture_and_Decisions.md) cho năm backend |

Kết luận: kỹ thuật MH1-MH9 đạt; chưa tuyên bố hoàn tất toàn bộ 10 MH khi thiếu MH10. Script verifier Day 02 kiểm contract MCP starter, luôn giữ `milestone_complete=false`; không thay acceptance của bốn backend/vendor hoặc quiz.

## Review implementation

- Giữ nguyên source `api/`, `web/`, `ingestion-worker/`, schema, base Compose và assertions verifier. Lab opt-in, không triển khai application lên Kubernetes.
- Binary/image/npm pins có nguồn upstream; Gateway prerelease được ghi rõ; không gọi mọi server là official Kubernetes/CNCF hoặc phổ biến ngang nhau.
- Filesystem chạy bằng signed image qua Docker MCP Gateway. Profile `insighthub-dev` pin digest, mount read-only, tắt network và chỉ cho ba read tools; snapshot được tạo lại để tránh file cũ tồn tại sau xóa source.
- Docker Gateway dùng POCI chính chủ; proxy là policy helper nhỏ có unit/live deny tests. Log bounded; response projection bỏ Env/Labels/Mounts; không đọc container ngoài lab.
- Prometheus MCP telemetry bind loopback port động, giải quyết lỗi port conflict khi Inspector/host chạy đồng thời. Backend query vẫn URL cố định; admin tools không bật.
- Host POCI giữ approval chuẩn; token SA hạn 6h; launch environment không kế thừa toàn bộ secrets của terminal.
- Kết quả regression và giới hạn môi trường nằm trong [Execution Report](../evidence/day2/Execution_Report.md). Application fixture chỉ phục vụ kiểm tra contract, MCP gọi backend thật.

## Bảy câu self-check (specification 6.9)

1. **Bốn backend và lý do?** Filesystem đọc source; Docker đọc container/log; Kubernetes đọc pod qua SA; Prometheus đọc metrics. Mỗi backend có process/pin/trace riêng. InsightHub là thứ năm để gắn domain ứng dụng.
2. **Server dùng read-only flag?** Kubernetes upstream có `--read-only`. Docker không dựa vào annotation: argv cố định và proxy API deny mutation. Filesystem chỉ expose ba read tools và mount snapshot `:ro` qua Gateway.
3. **SA có verbs gì?** get/list/watch trên resource được chọn, pods/log chỉ get. Không delete/create/patch, exec hoặc secrets; RoleBinding giới hạn insighthub. API server kiểm quyền bằng SA token.
4. **Filesystem root nào?** `/project`, tương ứng source snapshot trong `tmp/day2/source-view`, không `$HOME`. Không mount kubeconfig, credential hoặc toàn bộ checkout có ignored secrets.
5. **Server không kết nối debug thế nào?** Parse config, kiểm executable/checksum/path/flags, mở Inspector cùng config, xem initialization/console, invoke tool thật. Phân biệt transport closed với backend 403/forbidden; không chữa 403 bằng admin credential.
6. **Transport nào?** stdio cho mọi server local. Streamable HTTP là lựa chọn khác cho server dùng chung, cần auth/TLS và authorization theo caller, chưa cần trong lab.
7. **Ai bảo mật?** Host quyết định tool visibility/approval, client vận chuyển protocol và Roots, server validate input/output, backend/sandbox enforce quyền cuối. Prompt và annotation không thay RBAC hoặc isolation.
