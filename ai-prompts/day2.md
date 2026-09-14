# Day 2 — AI Prompt Log

**Dự án:** InsightHub RAG Notebook  
**Milestone:** MCP Protocol Integration  
**Host:** Codex CLI trên Windows  
**Model/version:** Không được ghi nhận trong phiên; không suy đoán phiên bản.  
**Quyết định:** Chấp nhận ba prompt theo cấu trúc bốn phần để tạo artifact Day 2 có thể review.  
**Thay đổi:** Tạo mới tệp log này; không thay đổi manifest, cấu hình host hay quyền cluster.  
**Kiểm tra thực chạy:** Xác nhận tệp đích chưa tồn tại trước khi khởi tạo; nội dung được kiểm tra theo số lượng ba prompt và các heading Markdown yêu cầu.

## Prompt 1 — Kubernetes RBAC Read-Only manifest

> **Ràng buộc:** Chỉ tạo hoặc cập nhật `mcp-rbac.yaml` trong phạm vi Day 2. Dùng ServiceAccount `mcp-readonly` và RBAC namespace-scoped cho namespace `insighthub`; chỉ cho phép đọc các resource cần thiết, gồm `get`, `list`, `watch`, và không cấp `create`, `update`, `patch`, `delete`, quyền `secrets`, `cluster-admin`, hoặc ClusterRoleBinding. Không đưa kubeconfig, token hay secret vào source.  
> **Mục tiêu:** Soạn manifest Kubernetes RBAC read-only cho Kubernetes MCP để quan sát tài nguyên InsightHub một cách an toàn.  
> **Tiêu chí thành công:** `mcp-rbac.yaml` hợp lệ, có ServiceAccount, Role và RoleBinding đúng namespace; `mcp-readonly` có thể `list pods` nhưng `delete pod` bị API server trả `Forbidden`.  
> **Ngữ cảnh:** InsightHub RAG Notebook — Day 2 MCP Protocol Integration. Kubernetes MCP là backend read-only; quyền phải được cưỡng chế bằng RBAC phía cluster, không chỉ bằng mô tả prompt/tool.

### Why it worked

Prompt đặt các verb bị cấm và resource nhạy cảm trước, vì vậy giới hạn quyền là đầu vào bắt buộc thay vì một đề xuất mơ hồ. Tiêu chí negative test cũng biến yêu cầu “read-only” thành bằng chứng có thể kiểm tra.

### What I changed

Tôi chỉ rõ `Role`/`RoleBinding` namespace-scoped thay cho quyền cluster-wide, thêm lệnh `watch` phục vụ quan sát, và loại trừ quyền Secrets cùng mọi verb ghi.

## Prompt 2 — Kiểm tra bốn MCP backends

> **Ràng buộc:** Chỉ dùng các MCP backend đã kết nối: Filesystem, Docker, Kubernetes và Prometheus. Chỉ thực hiện thao tác đọc; filesystem phải ở allowlist dự án, Kubernetes chỉ namespace `insighthub`, Docker không restart/xóa container, Prometheus không nhận raw PromQL tùy ý. Không in secret, token, kubeconfig, raw document content hoặc nhãn metric có dữ liệu nhạy cảm.  
> **Mục tiêu:** Kiểm tra trạng thái kết nối, liệt kê tool khả dụng và gọi một tool read-only tối thiểu từ từng MCP backend.  
> **Tiêu chí thành công:** Ghi rõ trạng thái Connected/Timeout/Error của từng backend, tên tool đã gọi và kết quả đã sanitize; Filesystem đọc metadata hoặc `README.md`, Docker quan sát container, K8s liệt kê Pod trong `insighthub`, Prometheus trả một chỉ số aggregate CPU/RAM hoặc nêu rõ không có series. Không coi fixture hay tool list là bằng chứng live nếu chưa có lời gọi live thành công.  
> **Ngữ cảnh:** InsightHub RAG Notebook — Day 2 MCP Protocol Integration. Bốn backend là yêu cầu tích hợp độc lập; tool discovery không thay thế kiểm tra quyền và lời gọi tool thực tế.

### Why it worked

Prompt gắn mỗi backend với một kiểm tra đọc tối thiểu và yêu cầu phân biệt rõ “connected”, “tool list” và “live call”. Điều này ngăn một backend timeout hoặc fixture bị ghi nhầm là đã vận hành thành công.

### What I changed

Tôi giới hạn bề mặt truy cập cho từng backend, thêm yêu cầu sanitize output và quy tắc báo cáo “không có series” thay vì suy diễn số liệu Prometheus bằng 0.

## Prompt 3 — Điều tra MCP timeout và Pod crash

> **Ràng buộc:** Chỉ điều tra và ghi nhận bằng chứng; không restart, xóa Pod/container, đổi RBAC, ghi đè `.codex/config.toml`, hoặc tiết lộ token/kubeconfig/log chứa dữ liệu nhạy cảm. Phân biệt dữ kiện quan sát được với giả thuyết. Với timeout, không tăng timeout vô hạn; với Pod crash, không kết luận nguyên nhân nếu chưa có log và trạng thái container.  
> **Mục tiêu:** Cập nhật `debug-session-day2.md` với hai case: MCP clients Filesystem/Docker/Kubernetes/Prometheus timeout khi Codex CLI khởi động (`startup_timeout_sec`) và chẩn đoán Pod/container bị crash bằng log, trạng thái cùng exit code. Đề xuất cấu hình timeout có kiểm soát trong `.codex/config.toml` và bước xác minh sau sửa.  
> **Tiêu chí thành công:** Tài liệu Markdown có bốn phần “Mục tiêu”, “Các tool/lệnh đã gọi”, “Phân tích từ AI Agent”, “Kết luận & Sửa đổi”; chứa log lỗi đã sanitize, nguyên nhân/phạm vi ảnh hưởng có mức độ chắc chắn rõ ràng, và phân biệt giải pháp startup timeout với xử lý nguyên nhân crash.  
> **Ngữ cảnh:** InsightHub RAG Notebook — Day 2 MCP Protocol Integration, chạy local Windows. Sự cố startup MCP có thể liên quan độ trễ npx/Node; RBAC read-only vẫn phải được kiểm chứng bằng API server, không chỉ dựa vào cấu hình MCP.

### Why it worked

Prompt ép tách timeout của lifecycle MCP khỏi root cause của Pod crash và yêu cầu evidence trước khi kết luận. Nhờ vậy, một thay đổi timeout chỉ được ghi là khắc phục khả năng khởi động client, không bị mô tả sai thành sửa lỗi workload.

### What I changed

Tôi bổ sung ranh giới không được mutation, yêu cầu log đã sanitize, và checklist xác minh sau sửa để tài liệu debug đủ dùng cho review Day 2 mà không biến thành runbook có quyền ghi.
