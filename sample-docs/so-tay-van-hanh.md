# Sổ tay vận hành InsightHub

## Giới thiệu

InsightHub là hệ thống RAG Notebook nội bộ, cho phép nhân viên upload tài liệu
và đặt câu hỏi dựa trên nội dung tài liệu đó. Hệ thống được dùng làm project
thực hành xuyên suốt module AI-Native DevOps.

## Kiến trúc

InsightHub gồm 5 thành phần chính sau khi hoàn thiện:

- web: giao diện người dùng viết bằng Next.js, cho phép upload tài liệu và chat.
- api: cổng API viết bằng FastAPI, điều phối luồng retrieval và sinh câu trả lời.
- ingestion-worker: tiến trình xử lý nền, chịu trách nhiệm chunk và embed tài liệu.
- redis: hàng đợi công việc và bộ nhớ đệm.
- postgres: cơ sở dữ liệu kèm extension pgvector để lưu vector embedding.

## Quy trình xử lý tài liệu

Khi người dùng upload một tài liệu, hệ thống thực hiện các bước: trích xuất văn bản,
chia nhỏ thành các đoạn (chunk), tạo vector embedding cho từng đoạn, và lưu vào
cơ sở dữ liệu vector. Sau khi hoàn tất, trạng thái tài liệu chuyển sang "ready".

## Chính sách sao lưu

Cơ sở dữ liệu PostgreSQL được sao lưu tự động mỗi ngày vào lúc 2 giờ sáng.
Bản sao lưu được giữ trong 30 ngày. Quản trị viên có thể khôi phục dữ liệu
từ bất kỳ bản sao lưu nào trong khoảng thời gian này.

## Liên hệ hỗ trợ

Mọi sự cố vận hành cần được báo cho đội DevOps qua kênh Slack #insighthub-ops.
Sự cố nghiêm trọng (hệ thống ngừng hoạt động) cần được báo ngay cho trưởng nhóm.
