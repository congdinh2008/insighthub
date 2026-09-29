# Day 05 - AI prompt log

- Yêu cầu người dùng: nghiên cứu yêu cầu Day 05, lập kế hoạch, không làm vượt phạm vi.
- Quyết định người dùng: tránh sửa code ứng dụng cho câu hỏi đếm ingestion; tập trung DevOps/Chatbot.
- Yêu cầu triển khai: hoàn thành plan và test E2E bằng Slack app `insighthub-do-2603`, workspace `InsightHub DO 2603`.
- Quyết định người dùng: dùng `#chatops-test`, tạo nếu thiếu; approver là tài khoản Slack đang đăng nhập.
- Điều chỉnh người dùng: dùng cloudflared đã cài trên máy thay ngrok.
- Xác nhận người dùng: chuyển Slack App từ Socket Mode sang HTTP Event Request URL của cloudflared.
- Xác nhận người dùng: cho phép gửi dữ kiện vận hành đã lọc tới Zenlayer hoặc DeepSeek để kiểm thử model; đã dùng Zenlayer đang có cấu hình hợp lệ.
- Chỉ đạo người dùng: để video screencast lại sau, bàn giao phần còn lại trước.

Prompt runtime duy nhất cho model nằm ở `chatops-bot/prompts/system.txt`. Logic định tuyến, phép đếm, quyền và approval được thực thi bằng code, không giao model quyết định. Sau khi được phép, Zenlayer `gpt-5.6-sol` tóm tắt dữ kiện health đã lọc trong một lượt Slack live; không nhận nội dung tài liệu hoặc token.
