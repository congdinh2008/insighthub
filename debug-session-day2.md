# Day 2 — MCP Debug Session

**Dự án:** InsightHub RAG Notebook  
**Phạm vi:** MCP Protocol Integration trên môi trường local Windows  
**Trạng thái:** Đã ghi nhận sự cố khởi động MCP và kiểm thử chặn thao tác ghi bằng RBAC.

## Mục tiêu

1. Điều tra lỗi các MCP client `filesystem`, `kubernetes`, `docker` và `prometheus` không hoàn tất khởi động khi Codex CLI kết nối qua stdio.
2. Xác minh rằng Kubernetes MCP chỉ có quyền đọc khi sử dụng ServiceAccount `mcp-readonly`: liệt kê Pod được phép, còn xóa Pod phải bị API server từ chối.
3. Ghi lại cách khắc phục có thể tái lập, không đưa kubeconfig, token, đường dẫn allowlist cụ thể hoặc dữ liệu nhạy cảm vào nhật ký.

## Các tool/lệnh đã gọi

### Case Study 1 — MCP client timeout khi khởi động

Các client MCP được Codex CLI khởi động qua `npx`/Node trên Windows:

| MCP client | Kết quả khởi động ban đầu |
| --- | --- |
| Filesystem | Timeout |
| Kubernetes | Timeout |
| Docker | Timeout |
| Prometheus | Timeout |

Lệnh/điểm kiểm tra sử dụng trong phiên debug:

```powershell
codex mcp list
codex mcp get filesystem
codex mcp get kubernetes
codex mcp get docker
codex mcp get prometheus
```

Sau khi sửa cấu hình, khởi động lại Codex CLI và chạy lại danh sách MCP để kiểm tra trạng thái kết nối. Không dùng `npx` với phiên bản thả nổi trong cấu hình nộp bài; phiên bản server phải được pin theo cấu hình Day 2 đã được phê duyệt.

### Case Study 2 — RBAC read-only của Kubernetes MCP

| Tool MCP | Identity chạy | Kết quả mong đợi/quan sát |
| --- | --- | --- |
| `kubernetes/list_pods` | ServiceAccount `mcp-readonly` | Thành công; chỉ đọc danh sách Pod trong namespace được cấp quyền. |
| `kubernetes/delete_pod` | ServiceAccount `mcp-readonly` | Bị từ chối `Forbidden`; không có Pod nào bị xóa. |

Lời gọi được kiểm thử với namespace lab `insighthub`:

```text
kubernetes/list_pods(namespace="insighthub")
kubernetes/delete_pod(namespace="insighthub", name="<pod-thu-nghiem>")
```

`delete_pod` là negative test có chủ đích. Không lặp lại bằng một Pod production hoặc bỏ qua lỗi quyền bằng cách đổi sang identity có đặc quyền cao hơn.

## Phân tích từ AI Agent

### Case Study 1 — Nguyên nhân `startup_timeout_sec`

Log lỗi thực tế trong phiên Codex CLI cho thấy bốn client không kịp hoàn tất handshake trước ngưỡng khởi động:

```text
MCP client filesystem: startup timeout (startup_timeout_sec)
MCP client kubernetes: startup timeout (startup_timeout_sec)
MCP client docker: startup timeout (startup_timeout_sec)
MCP client prometheus: startup timeout (startup_timeout_sec)
```

Triệu chứng đồng thời ở bốn server cho thấy đây không phải lỗi riêng của Kubernetes, Docker, Prometheus hoặc filesystem allowlist. Nguyên nhân gần nhất là độ trễ khởi tạo process `npx`/Node trên Windows — gồm resolve executable, nạp package đã pin và tạo stdio transport — vượt quá timeout mặc định của host. Đây là lỗi lifecycle của MCP client; chưa có bằng chứng cho lỗi RBAC, endpoint Prometheus, Docker daemon hay Kubernetes API ở giai đoạn đó.

Giải pháp là tăng timeout khởi động riêng cho từng server trong `%USERPROFILE%\\.codex\\config.toml` (không ghi credential vào file log). Ví dụ cấu trúc cấu hình:

```toml
[mcp_servers.filesystem]
# command, args và filesystem allowlist giữ theo cấu hình đã pin
startup_timeout_sec = 60

[mcp_servers.kubernetes]
# command, args, --read-only và kubeconfig của mcp-readonly giữ theo cấu hình đã pin
startup_timeout_sec = 60

[mcp_servers.docker]
# command và args của server đã pin
startup_timeout_sec = 60

[mcp_servers.prometheus]
# command, args và endpoint đã được allowlist
startup_timeout_sec = 60
```

Giá trị `60` giây là timeout khởi động, không phải timeout cho từng tool call. Sau khi thay đổi cần khởi động lại host, kiểm tra lại `tools/list` và gọi một tool read-only trên từng backend. Nếu còn timeout, cần thu log thời gian process khởi động và kiểm tra Node/npm cache, thay vì nâng timeout vô hạn.

### Case Study 2 — Bằng chứng RBAC là ranh giới thực thi

`list_pods` trả kết quả thành công, xác nhận ServiceAccount có verb `list` trên resource `pods` trong namespace `insighthub`. Lời gọi `delete_pod` bị Kubernetes API server trả về `Forbidden`, phù hợp với việc Role/RoleBinding của `mcp-readonly` không cấp verb `delete`:

```text
Error from Kubernetes API: Forbidden
serviceaccount:mcp-readonly cannot delete resource "pods" in namespace "insighthub"
```

Kết quả này chứng minh read-only được thực thi bởi RBAC phía cluster, không chỉ là mô tả tool hoặc prompt instruction. Cấu hình Kubernetes MCP vẫn cần giữ read-only/allowlist ở tầng server, nhưng các cờ đó là lớp phòng vệ bổ sung; ServiceAccount giới hạn quyền mới là ranh giới bắt buộc.

## Kết luận & Sửa đổi

1. **Khắc phục timeout:** thêm `startup_timeout_sec = 60` vào từng block MCP server trong `.codex/config.toml`, giữ lệnh và dependency ở phiên bản đã pin; sau đó restart Codex CLI và xác minh lại kết nối/từng lời gọi read-only.
2. **Bảo vệ quyền Kubernetes:** giữ Kubernetes MCP chạy bằng kubeconfig/identity của `mcp-readonly`, giới hạn namespace `insighthub`, không cấp `delete`, `patch`, `create` hoặc `update` cho Pod. Negative test `delete_pod` phải tiếp tục trả `Forbidden`.
3. **Tiêu chí đóng case:** cả bốn MCP phải hoàn thành startup và hiện tool list; filesystem chỉ truy cập allowlist; Docker/Prometheus chỉ dùng thao tác đọc theo cấu hình; K8s `list_pods` thành công và `delete_pod` bị chặn bởi RBAC.
4. **Theo dõi tiếp:** nếu lỗi khởi động tái diễn, lưu timestamp, phiên bản Codex/Node, thời gian khởi động từng server và thông báo lỗi đã sanitize. Không lưu token, kubeconfig, URL có credential hoặc output chứa dữ liệu nhạy cảm.
