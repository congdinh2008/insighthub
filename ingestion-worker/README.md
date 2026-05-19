# Ingestion worker - bắt buộc Day 1

Học viên tách sync ingestion thành Redis/ARQ + worker độc lập, hoàn thiện 5 thành phần. POST /documents trả 202; GET /documents chọn ID pending->ready/failed; retry/idempotency và dữ liệu atomic; chat không regression.

Đây là nền cho queue/backlog/anomaly Day 4 và ingestion intent Day 5, không phải extension tùy chọn. [Spec mục 5](../Running-Project-Specification-Student.md). Lệnh verify-day-1 mặc định kiểm tra async worker.
