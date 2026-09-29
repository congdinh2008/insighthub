# Day 05 - Rà soát và nghiệm thu đầy đủ ngày 29/09/2026

## Phạm vi

Đối chiếu specification mục 9, hoàn thiện các lỗi có thể làm sai kết quả vận hành, kiểm thử contract và kiểm thử giao diện trên Microsoft Edge bằng Computer Use. Giữ nguyên API, ingestion worker, schema và verifier. Dùng cluster kind-insighthub-local, namespace insighthub-dev và Slack #chatops-test hiện có.

## Quy trình và đầu ra

1. Rà soát MH1-MH11, ranh giới quyền, queue, audit và dữ liệu MCP.
2. Bổ sung regression tests cho lỗi tìm được, sửa bot và kiểm tra Python/Docker.
3. Khôi phục lab hiện có, refresh credentials scoped, chạy API/worker/tunnel.
4. Kiểm thử Slack: ba intent, destructive deny, approval chưa mutation, confirm, replay, expiry, restore. Kiểm tra InsightHub upload/chat trên Edge.
5. Lưu evidence mới, audit đã lọc, ảnh và video demo khoảng ba phút. Đối chiếu CI remote và tạo PR nếu chưa có; không tự merge.
6. Cập nhật self-check, runbook và bảng trạng thái với giới hạn thực tế.

## Phát hiện ban đầu

- Evidence cũ ngày 24/09, chưa có screencast và remote CI.
- Lab đã dừng; credentials Kubernetes sáu giờ cần refresh.
- Test hiện có chưa bao phủ đầy đủ dữ liệu MCP sai dạng, pod Pending/init failure, scalar scientific notation, timeout executor và approval expiry.
- Kiểm tra lại truy vấn fallback `or vector(0)` vì metric thiếu không được trình bày là không có lỗi.

## Tiêu chí bàn giao

Chỉ đánh dấu tiêu chí đạt khi có evidence của lượt chạy mới. Test fixture không thay live Slack/Edge. Nếu Loom hoặc external input không sẵn có, giữ phần đó pending và cung cấp artifact local tương ứng, không tuyên bố đủ nghiệm thu.
