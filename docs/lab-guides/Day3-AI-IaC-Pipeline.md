# Day 3 - AI-Powered IaC & Pipeline

Nguồn: mục 7 trong [Specification v3.3](../../Running-Project-Specification-Student.md), gồm đủ Must-have, Should-have, Nice-to-have, acceptance, submission, rubric và self-check.

## Đầu vào tích lũy
Day 1 async 5 thành phần và Day 2 MCP đã hoàn thiện.

## Công việc phải hoàn thiện
Viết SPEC và Terraform module EKS namespace/RDS pgvector/ElastiCache/IAM; S3 locking, private/encrypted/tagged resources; tflint/checkov/Conftest 3-layer defense; GitHub Actions fmt/lint/scan/policy/plan/cost/apply approval, OIDC và secret management; Helm deploy Kubernetes LIVE + HTTPS + smoke; evidence plan/run/artifact đúng source.

## Kiến thức và liên kết ngày sau
IaC/policy as code, OIDC/IRSA, managed services vs StatefulSet, environment/state và chi phí. Giữ nguyên task AWS; local validate không chứng minh AWS đã chạy.

## Cách kiểm chứng
Local Compose -> Helm/K8s trước, AWS khi đến bước cần xác minh AWS, xóa ngay sau lượt lab. Không thay Terraform/GitHub/Helm bằng Compose-only. DB/cache managed không tính thành pod.

## Tổ chức thực hành
Prework đọc nguồn và chuẩn bị môi trường. Lab 50 phút dành cho demo, xử lý phần khó và review. Phần triển khai còn lại phải hoàn thiện sau buổi; không tự chuyển nhiệm vụ bắt buộc thành mở rộng. Mỗi ngày nộp prompt log, source/PR và evidence đúng phiên bản theo specification.

[Guide local/AWS](../Guide_Local_AWS_Cost_DO2603.md) áp dụng mọi lượt chạy. Bộ tests/fixture chỉ kiểm chứng phạm vi ghi nhận, không thay đầu ra dự án thật.
