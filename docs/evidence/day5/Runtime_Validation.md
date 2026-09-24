# Day 05 - nghiệm thu ChatOps trên Slack thật

**Ngày:** 24/09/2026. **Môi trường:** `kind-insighthub-local`, namespace `insighthub-dev`, workspace `InsightHub DO 2603`, app `insighthub-do-2603`, kênh riêng `#chatops-test`. Bot nhận `app_mention` qua Cloudflare Quick Tunnel tới `/slack/events`, kiểm HMAC và đưa sự kiện vào Redis trước khi ACK. Đường tunnel chỉ trỏ tới cổng bot.

## Kết quả live

| Case | Tin nhắn gốc | Kết quả quan sát |
|---|---|---|
| Health | [Slack](https://insighthubdo2603.slack.com/archives/C0C3QBVE6AK/p1790249195855139) | API ready; không có pod/container lỗi; tỷ lệ 5xx/5 phút bằng 0. Bot nói rõ đây là tín hiệu kiểm tra, chưa kết luận toàn hệ thống. Audit `Ev0C410A4H9T` ghi lời gọi API, Kubernetes MCP và Prometheus MCP. |
| Ingestion hôm nay | [Slack](https://insighthubdo2603.slack.com/archives/C0C3QBVE6AK/p1790249258029019) | 0 tài liệu được tạo hôm nay theo ICT và hiện ready. Bot nêu rõ đây không phải số hoàn tất ingestion lần đầu. Audit `Ev0C49LCCARJ` ghi API `/documents` và Prometheus MCP. |
| Pods lỗi | [Slack](https://insighthubdo2603.slack.com/archives/C0C3QBVE6AK/p1790249337234399) | Không có pod/container lỗi trong 6 pods đang quan sát. Audit `Ev0C3QKDQ8MV` ghi Kubernetes MCP. |
| Lệnh destructive | [Slack](https://insighthubdo2603.slack.com/archives/C0C3QBVE6AK/p1790249373442299) | Bị từ chối, audit `Ev0C3ZPW3DRR`. |
| Scale 1 -> 2 | [Slack](https://insighthubdo2603.slack.com/archives/C0C3QBVE6AK/p1790249716018189) | Bot hỏi approval; deployment vẫn 1/1 trước confirm. Đúng approver xác nhận trong cùng thread, deployment thành 2/2; audit `Ev0C45U676D8`, `Ev0C3ZR2SF5Z`. |
| Dùng lại token | [Cùng thread scale](https://insighthubdo2603.slack.com/archives/C0C3QBVE6AK/p1790249716018189) | Bị từ chối, không scale; audit `Ev0C3ZR6D5UK`. |
| Restore 2 -> 1 | [Slack](https://insighthubdo2603.slack.com/archives/C0C3QBVE6AK/p1790249793179549) | Approval mới được xác nhận; deployment trở về 1/1; audit `Ev0C480MR51P`, `Ev0C480NGDEV`. |
| Zenlayer summary | [Slack](https://insighthubdo2603.slack.com/archives/C0C3QBVE6AK/p1790250537305089) | Bot thu thập lại API/Kubernetes MCP/Prometheus MCP, sau đó gắn "Nhận định AI (tham khảo)" từ Zenlayer `gpt-5.6-sol`; audit `Ev0C3ZTHGUR1`. Chỉ dữ kiện health đã lọc được gửi tới provider. |

File [audit.json](audit.json) là các bản ghi JSON đã lọc từ runtime JSONL, chỉ giữ các event Slack thật ở bảng trên. Không có signing secret, bot token, confirmation token, raw Slack body hay nội dung tài liệu. Các lần confirm hết hạn trước lượt thành công được giữ trong log runtime, không dùng để thay bằng chứng thành công.

## Phạm vi chứng minh

- Bài test contract cục bộ kiểm signature sai, binding/expiry/replay approval, dedup, ACK và worker recovery. Bot suite, static checks, Docker build và verifier được ghi riêng sau khi chạy lại.
- Read identity không đọc được Kubernetes Secret hay scale; scale identity chỉ update subresource `deployments/scale` của `insighthub-api`, không update deployment khác hoặc đọc Secret.
- Zenlayer summary được bật sau khi trainer chấp thuận riêng. Bot chỉ gửi dữ kiện health đã xác minh; model không quyết định intent, count hoặc approval. Lượt chạy đầu sau khi bật model có MCP path tương đối sai do working directory; bot trả trạng thái unknown/partial. Worker đã khởi động lại với working directory đúng; link Zenlayer summary ở bảng trên là lượt đạt đầy đủ ba nguồn.
- Quick Tunnel có URL tạm thời. Slack Event Request URL đã được xác thực tại lúc nghiệm thu; URL không phải endpoint production và sẽ không hoạt động nếu local process/tunnel dừng.
- Verifier Day 05 đã PASS 6 tests với `runtime_verified=true` cho contract cục bộ; bot suite 4/4, Ruff và Mypy PASS, Docker image build thành công. Regression smoke upload -> ready -> chat có citation cũng PASS, tạo tài liệu ID 22 sau snapshot ingestion 0 ở bảng trên. Bảng trên là bằng chứng Slack live độc lập.
- Video 3 phút chưa bàn giao. Bản capture đầu ghi nhầm cửa sổ foreground nên đã loại bỏ. Trainer yêu cầu để sau và bàn giao các phần còn lại trước; không dùng video sai làm evidence.
