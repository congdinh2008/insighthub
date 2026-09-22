# Day 02 - Quiz luyện tập và đáp án

Bộ 10 câu ôn tập theo learning objectives Day 02. Mỗi câu 1 điểm; mục tiêu tự kiểm tra >=7/10. Đây là answer key của solution, không phải đề/điểm quiz chính thức của lớp. MH10 cần kết quả trên quiz form được giao.

| # | Câu hỏi | Đáp án và lý do |
|---|---|---|
| 1 | Trong Codex kết nối Filesystem MCP, ai là Host, Client, Server? | Codex là host; session MCP bên trong host là client; process Filesystem là server expose tools. Model lựa chọn tool trong quyền host/backend cho phép |
| 2 | Bốn tool trên một InsightHub MCP có đủ MH2? | Không. Phải có bốn backend Filesystem, Docker/container, Kubernetes và Prometheus; số tool không bằng số backend |
| 3 | Phân biệt Tools, Resources, Prompts? | Tools là thao tác callable; Resources là dữ liệu có URI để đọc; Prompts là template tương tác server cung cấp. Server chỉ cần expose capabilities phù hợp, không bắt buộc tự thêm cả ba |
| 4 | Vì sao chọn stdio cho lab? | Host quản lý child process local, không mở public endpoint MCP. Streamable HTTP phù hợp server remote/shared và cần auth/transport security |
| 5 | Có ClusterRole read-only thì quyền tự giới hạn namespace? | Không. RoleBinding trong insighthub mới giới hạn grant theo namespace. ClusterRoleBinding sẽ cấp scope rộng hơn |
| 6 | SA mcp-readonly có được delete pod hoặc get Secret? | Không. Chỉ read verbs trên resource allowlist; Secret/exec không thuộc grant. Kiểm bằng chính kubeconfig SA |
| 7 | Filesystem chỉ khai báo /project đã đủ bảo vệ host? | Chưa đủ. Cần kiểm canonical paths/symlink và sandbox mount; Roots có thể đổi allow-list. Solution chỉ mount snapshot sạch read-only và network none |
| 8 | Docker socket mount :ro và readOnlyHint có chặn POST Docker API? | Không. Socket :ro không lọc API, annotation không là authorization. Solution enforce argv cố định và HTTP read proxy deny mutation |
| 9 | Inspector Connected và tools/list có đủ MH3/MH8? | Chưa. MH8 cần invoke tool thành công và screenshot; MH3 cần host/model call thật từng backend với input/output/time. SDK/CLI không thay host evidence |
| 10 | Log báo thiếu env, sửa env rồi docker restart đã đủ? | Chưa. Restart giữ env cũ; operator recreate đúng service với cấu hình hợp lệ, MCP đọc lại status/log để xác nhận phục hồi |

Khi có quiz chính thức, học viên lưu ngày làm, link bài và điểm thật trong submission. Không lấy điểm tự chấm từ bảng đáp án làm bằng chứng MH10.
