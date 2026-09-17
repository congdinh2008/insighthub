# Day 3 — AI Prompt Log

## Prompt 1 — Tạo `infra/SPEC.md`

### Mục tiêu

Đọc repository và tài liệu Day 3, sau đó tạo `infra/SPEC.md` cho hạ tầng
InsightHub. Chỉ viết specification, chưa sinh Terraform code.

### Ràng buộc (Constraints)

- Namespace EKS là `insighthub-dev`; RDS PostgreSQL 16 có pgvector,
  encryption at rest và private/not public; ElastiCache Redis 7 private/not
  public.
- Dùng IRSA cho ServiceAccount `insighthub`, không IAM User/access key dài hạn.
- S3 backend encrypted với `use_lockfile = true`; tags bắt buộc là `project`,
  `environment`, `owner`, `cost_center`, `managed_by="terraform"`.
- Pin Terraform `>= 1.7.0, < 2.0.0` và AWS provider `~> 5.70`; không hard-code
  credential hay AWS Account ID; region không có trong tài liệu phải ghi TBD.
- Không mở RDS/Redis ra `0.0.0.0/0`, không tạo `*.tf`, không chạy Terraform.

### Tiêu chí thành công

`infra/SPEC.md` có các mục Overview, Requirements, Constraints, Networking,
EKS, RDS, Redis, IAM/IRSA, Backend, Tags, Inputs/Outputs và Acceptance
Criteria; mọi thông tin chưa có được ghi TBD.

### Ngữ cảnh tham chiếu

Đọc `infra/`, `docs/lab-guides/Day3-AI-IaC-Pipeline.md`,
`Running-Project-Specification-Student.md` và
`docs/Guide_Local_AWS_Cost_DO2603.md`.

## Prompt 2 — Sinh Terraform từ `infra/SPEC.md`

### Mục tiêu

Đọc `infra/SPEC.md` và sinh bộ mã Terraform trong `infra/` để khởi tạo hạ tầng
InsightHub.

### Ràng buộc (Constraints)

- Dùng `main.tf`, `variables.tf`, `outputs.tf`, `providers.tf`, `backend.tf`
  và `modules/`.
- Backend S3 encrypted, dùng native locking `use_lockfile = true`; không chứa
  credential hoặc Account ID.
- RDS PostgreSQL 16 và Redis 7 chỉ dùng private subnet; RDS có
  `storage_encrypted = true` và không public; không có ingress RDS/Redis từ
  `0.0.0.0/0`.
- Cấu hình IRSA cho ServiceAccount `insighthub` ở `insighthub-dev`, không tạo
  IAM User; gắn năm tags bắt buộc cho mọi AWS resource hỗ trợ tags.
- Pin Terraform `>= 1.7.0, < 2.0.0` và AWS provider `~> 5.70`.

### Tiêu chí thành công

`terraform fmt -check -recursive` và `terraform validate` thành công, với
namespace, IRSA, RDS, Redis, VPC/private subnet và backend được khai báo trong
source.

### Ngữ cảnh tham chiếu

Đọc `infra/SPEC.md`, cấu trúc `infra/` hiện có, schema
`infra/db/init.sql` và tài liệu Day 3.

## Prompt 3 — Tạo `.github/workflows/iac.yml`

### Mục tiêu

Tạo `.github/workflows/iac.yml` triển khai CI/CD pipeline Terraform cho
InsightHub.

### Ràng buộc (Constraints)

- Xác thực AWS qua OIDC role bằng `aws-actions/configure-aws-credentials`,
  không dùng long-lived AWS Access Keys.
- Có các jobs: fmt + tflint; Checkov security scan; Conftest Rego policy check;
  Terraform plan + Infracost; Terraform apply.
- Apply chỉ chạy khi push lên `main` hoặc `prod` và dùng GitHub environment có
  protection/manual approval.
- Pin action ở SHA hoặc phiên bản cố định; dùng backend/biến cấu hình qua
  GitHub variables và Infracost API key qua GitHub secret, không hard-code
  credential.

### Tiêu chí thành công

`.github/workflows/iac.yml` đúng cú pháp YAML, chạy các stage theo thứ tự gate,
và chỉ có đường xác thực AWS qua OIDC role.

### Ngữ cảnh tham chiếu

Đọc `infra/SPEC.md`, Terraform source trong `infra/`,
`.github/workflows/starter.yml`, tài liệu Day 3 và cost guide; dùng
`policy/terraform/` cho Conftest Rego policy.
