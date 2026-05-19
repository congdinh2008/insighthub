# Day 4 - AIOps + MLOps Overview

Nguồn: mục 8 trong [Specification v3.3](../../Running-Project-Specification-Student.md), gồm đủ Must-have, Should-have, Nice-to-have, acceptance, submission, rubric và self-check.

## Đầu vào tích lũy
Deployment Day 3 và async worker Day 1 có thật; dùng telemetry baseline local>=1h, không giữ cloud chạy giữa buổi.

## Công việc phải hoàn thiện
ServiceMonitor/exporters đủ 5 thành phần; dashboard9+ panels rate/errors/duration/queue/token/latency/cost/pod/deploy; recording/anomaly rules cho latency, backlog, error; Alertmanager->Slack; inject đủ3 incidents và3 RCA có metric/timestamp; MLOps notes4 blocks và quiz5 câu.

## Kiến thức và liên kết ngày sau
RED/USE, statistical vs ML anomaly, correlation, evidence-first RCA; ML lifecycle, Registry/Approval Gate/Drift/Rollback, ownership DevOps vs ML.

## Cách kiểm chứng
Mỗi incident phải có baseline/failure/recovery, kiểm chứng rules bằng promtool, tín hiệu/alert thật. Một incident không thay ba. Collector hiện hành có thể dùng Alloy, không làm mất observability/MLOps task.

## Tổ chức thực hành
Prework đọc nguồn và chuẩn bị môi trường. Lab 50 phút dành cho demo, xử lý phần khó và review. Phần triển khai còn lại phải hoàn thiện sau buổi; không tự chuyển nhiệm vụ bắt buộc thành mở rộng. Mỗi ngày nộp prompt log, source/PR và evidence đúng phiên bản theo specification.

[Guide local/AWS](../Guide_Local_AWS_Cost_DO2603.md) áp dụng mọi lượt chạy. Bộ tests/fixture chỉ kiểm chứng phạm vi ghi nhận, không thay đầu ra dự án thật.
