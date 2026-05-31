# DAY 03 — AI-Powered IaC & CI/CD
## Hướng dẫn Mentor: Terraform, Policy Gate & Deploy InsightHub

> **Đối tượng:** Trainer / Mentor hướng dẫn học viên  
> **Thời lượng:** 2.5 giờ (150 phút)  
> **Ngày:** Day 3 trong Module 7 — AI-Native DevOps  
> **Branch học viên làm việc:** `day3-terraform`

---

## Mục lục

1. [Tổng quan & Mục tiêu](#1-tổng-quan--mục-tiêu)
2. [Chuẩn bị trước buổi](#2-chuẩn-bị-trước-buổi)
   - [2.1. Kiểm tra toolchain](#21-kiểm-tra-toolchain)
   - [2.2. Kiểm tra repo Day 3](#22-kiểm-tra-repo-day-3)
   - [2.3. Chuẩn bị AWS backend](#23-chuẩn-bị-aws-backend-s3--dynamodb)
   - [2.4. Chuẩn bị GitHub OIDC](#24-chuẩn-bị-github-oidc-không-dùng-long-lived-aws-keys)
   - [2.5. Chuẩn bị GitHub Environments](#25-chuẩn-bị-github-environments-manual-approval-gate)
   - [2.6. Chuẩn bị Infracost](#26-chuẩn-bị-infracost-cost-estimate-trên-pr)
   - [2.7. Checklist trước khi bắt đầu](#27-checklist-trước-khi-bắt-đầu-day-3)
3. [Cấu trúc buổi học](#3-cấu-trúc-buổi-học)
4. [Segment 1 — Recap Day 2 & Hook](#4-segment-1--recap-day-2--hook)
5. [Segment 2 — Concept: 3-Layer Defense cho IaC](#5-segment-2--concept-3-layer-defense-cho-iac)
6. [Segment 3 — Terraform Architecture Walkthrough](#6-segment-3--terraform-architecture-walkthrough)
7. [Segment 4 — Live Demo: Policy Gate + Pipeline](#7-segment-4--live-demo-policy-gate--pipeline)
8. [Segment 5 — Deploy & Smoke Test](#8-segment-5--deploy--smoke-test)
9. [Artifact Checklist](#9-artifact-checklist)
10. [Troubleshooting Guide](#10-troubleshooting-guide)
11. [Q&A Bank](#11-qa-bank)

---

## 1. Tổng quan & Mục tiêu

### Bức tranh lớn

Day 2 giúp AI agent nhìn được Docker/Kubernetes qua MCP. Day 3 chuyển từ debug sang **tạo hạ tầng có kiểm soát**: học viên dùng AI sinh Terraform và GitHub Actions, nhưng mọi thay đổi phải qua human review và policy gate.

**Thông điệp chính:** AI có thể sinh IaC nhanh, nhưng không được apply nếu chưa qua 3 lớp phòng thủ:

1. **AI generate** — sinh module, pipeline, policy.
2. **Human review** — đọc plan, hiểu blast radius.
3. **Policy gate** — `terraform fmt`, `validate`, `tflint`, `checkov`, `conftest`, Infracost.

### Mục tiêu học viên đạt được cuối Day 3

| # | Mục tiêu | Verify |
|---|---|---|
| 1 | Giải thích kiến trúc AWS cho InsightHub | VPC/EKS/RDS/Redis/IRSA diagram |
| 2 | Terraform module hóa rõ ràng | `infra/modules/*` + root orchestration |
| 3 | Chạy policy gate trước plan/apply | fmt/validate/tflint/checkov/conftest |
| 4 | Hiểu GitHub Actions OIDC pipeline | `.github/workflows/iac.yml` |
| 5 | Deploy InsightHub lên K8s dev | `kubectl get pods -n insighthub-dev` |
| 6 | Smoke test upload → ingest → chat | `scripts/smoke-test.sh` |

### Artifact học viên nộp

```text
1. infra/                         — Terraform root + modules
2. infra/policies/                — Rego policy gate
3. .github/workflows/iac.yml       — multi-stage IaC pipeline
4. GitHub Actions run URL          — pipeline evidence
5. InsightHub live URL hoặc minikube demo URL
6. Smoke test evidence             — health/upload/chat
```

---

## 2. Chuẩn bị trước buổi

### 2.1. Kiểm tra toolchain

```bash
terraform version       # >= 1.9
aws --version           # AWS CLI v2
kubectl version --client
helm version
tflint --version
checkov --version
conftest --version
gh --version
```

> **Mentor note:** Nếu `tflint` trên macOS báo plugin handshake lỗi, chạy policy gate trong GitHub Actions/Linux runner hoặc reinstall TFLint. Terraform validate và Checkov vẫn có thể chạy local để debug nhanh.

### 2.2. Kiểm tra repo Day 3

```bash
find infra -maxdepth 3 -type f | sort
find .github/workflows -maxdepth 1 -type f | sort
```

Cấu trúc mong đợi:

```text
infra/
├── backend.tf
├── backend-dev.hcl
├── main.tf
├── providers.tf
├── variables.tf
├── outputs.tf
├── locals.tf
├── modules/
│   ├── cache/
│   ├── database/
│   ├── irsa/
│   └── networking/
├── policies/
│   ├── encryption.rego
│   ├── no_public_resources.rego
│   └── required_tags.rego
└── helm/
    └── insighthub/
```

### 2.3. Chuẩn bị AWS backend (S3 + DynamoDB)

Terraform state cần được lưu trên remote backend có versioning, encryption, và lock. Chạy lần đầu trước khi `terraform init`.

**Biến môi trường** — đặt trước để tái dùng trong các lệnh bên dưới:

```bash
export AWS_REGION="ap-southeast-1"
export ENV="dev"                             # dev | staging | prod
export TF_BUCKET="insighthub-tfstate-${ENV}"
export TF_LOCK_TABLE="insighthub-tflock-${ENV}"
export AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
```

**Bước 1 — Tạo S3 bucket:**

```bash
# ap-southeast-1 yêu cầu LocationConstraint
aws s3api create-bucket \
  --bucket "${TF_BUCKET}" \
  --region "${AWS_REGION}" \
  --create-bucket-configuration LocationConstraint="${AWS_REGION}"
```

**Bước 2 — Bật versioning** (bắt buộc để rollback state):

```bash
aws s3api put-bucket-versioning \
  --bucket "${TF_BUCKET}" \
  --versioning-configuration Status=Enabled
```

**Bước 3 — Chặn public access** (state file không được public):

```bash
aws s3api put-public-access-block \
  --bucket "${TF_BUCKET}" \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

**Bước 4 — Bật server-side encryption** (AES-256 đủ cho lab; prod dùng KMS):

```bash
aws s3api put-bucket-encryption \
  --bucket "${TF_BUCKET}" \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
      "BucketKeyEnabled": true
    }]
  }'
```

**Bước 5 — Bật access logging** (audit ai đã đọc/sửa state):

```bash
# Tạo log bucket riêng
aws s3api create-bucket \
  --bucket "${TF_BUCKET}-logs" \
  --region "${AWS_REGION}" \
  --create-bucket-configuration LocationConstraint="${AWS_REGION}"

aws s3api put-bucket-acl \
  --bucket "${TF_BUCKET}-logs" \
  --acl log-delivery-write

aws s3api put-bucket-logging \
  --bucket "${TF_BUCKET}" \
  --bucket-logging-status '{
    "LoggingEnabled": {
      "TargetBucket": "'"${TF_BUCKET}-logs"'",
      "TargetPrefix": "tfstate-access/"
    }
  }'
```

**Bước 6 — Tạo DynamoDB table** cho state locking:

```bash
aws dynamodb create-table \
  --table-name "${TF_LOCK_TABLE}" \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region "${AWS_REGION}"

# Bật Point-in-Time Recovery
aws dynamodb update-continuous-backups \
  --table-name "${TF_LOCK_TABLE}" \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
  --region "${AWS_REGION}"
```

**Bước 7 — Verify:**

```bash
aws s3api get-bucket-versioning      --bucket "${TF_BUCKET}" --region "${AWS_REGION}"
aws s3api get-public-access-block    --bucket "${TF_BUCKET}" --region "${AWS_REGION}"
aws s3api get-bucket-encryption      --bucket "${TF_BUCKET}" --region "${AWS_REGION}"
aws dynamodb describe-table --table-name "${TF_LOCK_TABLE}" --region "${AWS_REGION}" \
  --query 'Table.TableStatus'
```

Kết quả mong đợi: versioning `Enabled`, 4 public-access block đều `true`, encryption `AES256`, table status `ACTIVE`.

**Bước 8 — Cập nhật `infra/backend-dev.hcl`** với bucket name thực:

```hcl
bucket         = "insighthub-tfstate-dev"
key            = "insighthub/dev/terraform.tfstate"
region         = "ap-southeast-1"
encrypt        = true
dynamodb_table = "insighthub-tflock-dev"
```

Sau đó init với backend thật:

```bash
cd infra
terraform init -backend-config=backend-dev.hcl -reconfigure
```

---

### 2.4. Chuẩn bị GitHub OIDC (không dùng long-lived AWS keys)

GitHub Actions dùng OpenID Connect để lấy AWS credentials tạm thời. **Không có `AWS_ACCESS_KEY_ID` hay `AWS_SECRET_ACCESS_KEY` nào được lưu trong repo.**

**Tổng quan flow:**

```
GitHub Actions job
  → Request OIDC JWT từ GitHub
  → AWS STS AssumeRoleWithWebIdentity
  → Nhận credentials tạm (15–60 phút)
  → Terraform plan/apply với credentials đó
```

#### Bước 1 — Tạo OIDC Provider trong AWS (một lần duy nhất per account)

Kiểm tra trước xem đã có chưa:

```bash
aws iam list-open-id-connect-providers \
  --query 'OpenIDConnectProviderList[].Arn' --output text
```

Nếu chưa có `token.actions.githubusercontent.com`, tạo mới:

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 1c58a3a8518e8759bf075b76b750d4f2df264fcd

echo "OIDC Provider ARN:"
aws iam list-open-id-connect-providers \
  --query 'OpenIDConnectProviderList[?contains(Arn,`githubusercontent`)].Arn' \
  --output text
```

> **Lưu ý:** Thumbprint là SHA-1 của root CA của GitHub — không thay đổi thường xuyên. Kiểm tra giá trị hiện tại tại [GitHub OIDC docs](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect).

#### Bước 2 — Tạo Trust Policy

```bash
export GITHUB_ORG="congdinh2008"     # GitHub username hoặc org
export GITHUB_REPO="insighthub"

cat > /tmp/github-actions-trust.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GitHubActionsOIDC",
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF

cat /tmp/github-actions-trust.json  # verify trước khi tạo
```

> **Security note:** `sub: repo:OWNER/REPO:*` cho phép mọi branch/PR của repo này. Nếu muốn chặt hơn, dùng `repo:OWNER/REPO:ref:refs/heads/main` chỉ cho phép main branch.

#### Bước 3 — Tạo IAM Role

```bash
aws iam create-role \
  --role-name insighthub-github-actions \
  --assume-role-policy-document file:///tmp/github-actions-trust.json \
  --description "GitHub Actions OIDC role for InsightHub IaC pipeline" \
  --max-session-duration 3600

# Lấy ARN
export OIDC_ROLE_ARN=$(aws iam get-role \
  --role-name insighthub-github-actions \
  --query Role.Arn --output text)
echo "Role ARN: ${OIDC_ROLE_ARN}"
```

#### Bước 4 — Gắn IAM Policy

Pipeline cần quyền để Terraform plan/apply toàn bộ stack (EKS, RDS, ElastiCache, IAM, KMS, VPC...).

**Option A — Lab/học tập** (đủ quyền để học viên không bị blocked):

```bash
aws iam attach-role-policy \
  --role-name insighthub-github-actions \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

**Option B — Production** (scoped policy, viết tay hoặc dùng `policy-sentry`):

```bash
# Tạo scoped policy cho các service InsightHub cần
cat > /tmp/insighthub-iac-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CoreInfra",
      "Effect": "Allow",
      "Action": [
        "ec2:*", "eks:*", "rds:*", "elasticache:*",
        "kms:*", "secretsmanager:*", "iam:*",
        "logs:*", "cloudwatch:*", "s3:*", "dynamodb:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-southeast-1"
        }
      }
    },
    {
      "Sid": "TerraformState",
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::insighthub-tfstate-*",
        "arn:aws:s3:::insighthub-tfstate-*/*"
      ]
    },
    {
      "Sid": "TerraformLock",
      "Effect": "Allow",
      "Action": ["dynamodb:GetItem","dynamodb:PutItem","dynamodb:DeleteItem"],
      "Resource": "arn:aws:dynamodb:ap-southeast-1:*:table/insighthub-tflock-*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name insighthub-github-actions-policy \
  --policy-document file:///tmp/insighthub-iac-policy.json

aws iam attach-role-policy \
  --role-name insighthub-github-actions \
  --policy-arn "arn:aws:iam::${AWS_ACCOUNT}:policy/insighthub-github-actions-policy"
```

#### Bước 5 — Lưu secret vào GitHub repository

```bash
# Kiểm tra GitHub CLI đã auth chưa
gh auth status

# Set secret
gh secret set AWS_OIDC_ROLE_ARN \
  --body "${OIDC_ROLE_ARN}" \
  --repo "${GITHUB_ORG}/${GITHUB_REPO}"

# Verify
gh secret list --repo "${GITHUB_ORG}/${GITHUB_REPO}"
```

#### Bước 6 — Verify OIDC end-to-end

> **Quan trọng — giới hạn của `workflow_dispatch`:**
> GitHub chỉ xử lý trigger `workflow_dispatch` khi file `iac.yml` đã có trên **default branch** (`main`). Khi đang làm việc trên branch `day3-terraform` (chưa merge), `gh workflow run` sẽ báo lỗi:
> ```
> could not create workflow dispatch event: HTTP 422: Workflow does not have 'workflow_dispatch' trigger
> ```
> Đây không phải lỗi OIDC — đây là giới hạn của GitHub.

**Option A — Kiểm tra OIDC trước khi merge (dùng `push` trigger):**

File `iac.yml` đã cấu hình `push.branches: [main, "day*-*"]`, nên pipeline tự động chạy khi push lên branch `day3-*`:

```bash
# Trigger CI bằng cách push một thay đổi nhỏ
cd infra && touch .trigger-ci && git add .trigger-ci
git commit -m "chore: trigger CI test" && git push

# Theo dõi run
gh run list --repo "${GITHUB_ORG}/${GITHUB_REPO}" --limit 3
gh run watch --repo "${GITHUB_ORG}/${GITHUB_REPO}"
```

Xóa file sau khi test xong:

```bash
git rm infra/.trigger-ci && git commit -m "chore: remove CI trigger file" && git push
```

**Option B — Kiểm tra sau khi merge vào `main`:**

```bash
# Sau khi PR được merge vào main, workflow_dispatch hoạt động bình thường
gh workflow run iac.yml \
  --repo "${GITHUB_ORG}/${GITHUB_REPO}" \
  --field environment=dev \
  --field apply=false

# Theo dõi
gh run watch --repo "${GITHUB_ORG}/${GITHUB_REPO}"
```

**Kết quả mong đợi:**

- Jobs `fmt`, `lint`, `security-scan` pass (không cần AWS credentials).
- Jobs `policy-check`, `plan` pass nếu OIDC đúng → thấy `terraform plan` output.
- Jobs `policy-check`, `plan` fail với `"Error: Not authorized"` hoặc `"could not assume role"` → OIDC trust policy sai, xem lại bước 1–4.
- Job `apply` không chạy (chỉ chạy khi `apply=true` và environment approved).

---

### 2.5. Chuẩn bị GitHub Environments (manual approval gate)

Job `apply` trong `iac.yml` cần GitHub Environment với protection rule để yêu cầu human approval trước khi apply lên cloud.

#### Tạo Environments qua GitHub UI

Vào: **Settings → Environments → New environment**

| Environment | Protection rules | Dùng khi |
|---|---|---|
| `dev` | Không cần reviewer | Tự động sau plan |
| `staging` | 1 reviewer (tech lead) | PR merge vào staging |
| `prod` | 2 reviewers + deployment branch `main` only | Release |

#### Tạo Environments qua GitHub CLI (dev không cần reviewer)

```bash
# dev — không cần reviewer, chạy ngay
gh api --method PUT \
  "/repos/${GITHUB_ORG}/${GITHUB_REPO}/environments/dev" \
  --field wait_timer=0

# prod — yêu cầu 1 reviewer là bản thân (thay <your-github-user-id>)
MY_USER_ID=$(gh api /user --jq '.id')
gh api --method PUT \
  "/repos/${GITHUB_ORG}/${GITHUB_REPO}/environments/prod" \
  --raw-field "reviewers=[{\"type\":\"User\",\"id\":${MY_USER_ID}}]" \
  --field wait_timer=0

# Verify
gh api "/repos/${GITHUB_ORG}/${GITHUB_REPO}/environments" \
  --jq '.environments[].name'
```

> **Lưu ý cho học viên:** Nếu repo là public, GitHub Environments tự do. Nếu repo private và account free, protection rules không available — dùng `main` branch protection thay thế.

---

### 2.6. Chuẩn bị Infracost (cost estimate trên PR)

Job `cost-estimate` trong pipeline cần Infracost API key để post comment chi phí lên PR.

```bash
# 1. Đăng ký tại https://www.infracost.io/docs/ (free tier đủ dùng)
# 2. Lấy API key từ dashboard

# 3. Lưu vào GitHub secret
gh secret set INFRACOST_API_KEY \
  --body "<your-infracost-api-key>" \
  --repo "${GITHUB_ORG}/${GITHUB_REPO}"

# 4. Test local (optional)
infracost breakdown --path infra/ \
  --terraform-var="environment=dev" \
  --format table
```

Kết quả mong đợi: tổng chi phí dev env < $50/tháng (NAT Gateway + EKS + RDS t3.medium + ElastiCache t3.micro).

---

### 2.7. Checklist trước khi bắt đầu Day 3

```bash
# Chạy từ root repo
echo "=== AWS ===" && \
  aws sts get-caller-identity --query '[Account,Arn]' --output text && \
  aws s3api head-bucket --bucket insighthub-tfstate-dev 2>&1 && \
  aws dynamodb describe-table --table-name insighthub-tflock-dev \
    --query 'Table.TableStatus' --output text && \
echo "=== GitHub ===" && \
  gh auth status && \
  gh secret list --repo "${GITHUB_ORG}/${GITHUB_REPO}" && \
  gh api "/repos/${GITHUB_ORG}/${GITHUB_REPO}/environments" --jq '.environments[].name' && \
echo "=== Terraform ===" && \
  cd infra && terraform init -backend-config=backend-dev.hcl && \
  terraform fmt -check -recursive && \
  terraform validate && \
echo "=== Tools ===" && \
  tflint --version && checkov --version && helm version --short && conftest --version
```

Tất cả output không có `Error` → sẵn sàng bắt đầu.

---

## 3. Cấu trúc buổi học

| Thời gian | Segment | Nội dung |
|---|---|---|
| 0:00-0:10 | Recap & Hook | Từ MCP debug sang AI-generated IaC |
| 0:10-0:40 | Concept | 3-Layer Defense, blast radius, policy gate |
| 0:40-1:15 | Terraform Walkthrough | root module, local modules, AWS managed services |
| 1:15-1:55 | Live Demo | fmt/validate/checkov/conftest + GitHub Actions |
| 1:55-2:20 | Deploy | Helm deploy app, verify pods, smoke test |
| 2:20-2:30 | Consolidation | Rubric, pitfalls, submission |

---

## 4. Segment 1 — Recap Day 2 & Hook

Hỏi học viên:

- "Day 2, AI agent debug được gì nhờ MCP?"
- "Nếu để AI tự tạo hạ tầng cloud, rủi ro lớn nhất là gì?"
- "Một Terraform plan có `destroy` bất ngờ thì xử lý thế nào?"

Hook demo:

```text
Prompt cho AI:
"Generate Terraform for InsightHub on AWS: EKS, RDS PostgreSQL, Redis, IRSA."

Sau đó hỏi:
"Nếu apply ngay thì có thể sai ở đâu?"
```

Chốt ý: Day 3 không dạy "AI viết Terraform thay mình"; Day 3 dạy cách biến AI output thành hạ tầng reviewable, testable, policy-controlled.

---

## 5. Segment 2 — Concept: 3-Layer Defense cho IaC

### Layer 1 — AI Generate

AI sinh code nhanh, nhưng output chỉ là draft:

```text
Spec → AI prompt → Terraform module → review
```

Prompt tốt phải có constraints:

- AWS region, environment.
- Non-public RDS/Redis.
- Encryption at rest/in transit.
- Required tags.
- IRSA, không IAM user.
- Cost limit cho dev.

### Layer 2 — Human Review

Mentor nhấn mạnh 4 câu hỏi trước apply:

1. Plan có destroy không?
2. Resource có public không?
3. Secret có bị hardcode không?
4. Chi phí dev có hợp lý không?

### Layer 3 — Policy Gate

```bash
terraform fmt -check -recursive
terraform validate
tflint --recursive
checkov -d infra --soft-fail-on LOW,MEDIUM --quiet
terraform plan -out=tfplan.binary
terraform show -json tfplan.binary > tfplan.json
conftest test --policy infra/policies/ tfplan.json
```

---

## 6. Segment 3 — Terraform Architecture Walkthrough

### 6.1. Root module

Root module ở `infra/` chỉ orchestration:

- AWS provider + Kubernetes provider + Helm provider.
- VPC module.
- EKS module.
- Kubernetes namespace.
- KMS keys.
- Local modules: `networking`, `database`, `cache`, `irsa`.

### 6.2. Local modules

| Module | Trách nhiệm |
|---|---|
| `modules/networking` | Security groups cho RDS/Redis, chỉ allow từ EKS node SG |
| `modules/database` | RDS PostgreSQL 16, parameter group, DB password trong Secrets Manager |
| `modules/cache` | ElastiCache Redis 7, TLS/auth token, token trong Secrets Manager |
| `modules/irsa` | IAM role least-privilege cho ServiceAccount `insighthub-api` |

### 6.3. Best practice đã áp dụng

- Remote backend S3 + DynamoDB lock.
- Provider versions pinned.
- Common tags: `project`, `environment`, `owner`, `cost_center`, `managed_by`.
- RDS `publicly_accessible = false`.
- Redis private subnet, auth token, TLS, encryption at rest.
- KMS key rotation enabled.
- Secrets Manager cho DB password và Redis token.
- IRSA thay vì IAM user/static key.
- Rego policy cho encryption, public access, required tags.

---

## 7. Segment 4 — Live Demo: Policy Gate + Pipeline

### 7.1. Local checks

```bash
cd infra

terraform init -backend=false
terraform fmt -check -recursive
terraform validate
checkov -d . --soft-fail-on LOW,MEDIUM --quiet
```

Nếu backend AWS đã sẵn sàng:

```bash
terraform init -backend-config=backend-dev.hcl
terraform plan -var="environment=dev" -out=tfplan.binary
terraform show -json tfplan.binary > tfplan.json
conftest test --policy policies/ --input json tfplan.json
```

### 7.2. GitHub Actions pipeline

Workflow: `.github/workflows/iac.yml`

Expected jobs:

```text
fmt → lint → security-scan → policy-check → plan → cost-estimate → apply
```

Kiểm tra:

```bash
gh workflow view iac.yml
gh run list --workflow=iac.yml --limit 5
gh run view <run-id> --json conclusion,jobs,url
```

Mentor note:

- `policy-check` và `plan` không được `continue-on-error`.
- Nếu OIDC fail, pipeline phải fail thật.
- `apply` chỉ chạy khi manual `workflow_dispatch` với `apply=true` và environment approval.

---

## 8. Segment 5 — Deploy & Smoke Test

### 8.1. Deploy dev bằng minikube

Dùng khi lớp chưa provision AWS thật:

```bash
eval $(minikube docker-env)

docker build -t insighthub-api:latest ./api/
docker build -t insighthub-worker:latest ./ingestion-worker/
docker build -t insighthub-web:latest ./web/

helm upgrade --install insighthub infra/helm/insighthub \
  -f infra/helm/values-dev.yaml \
  -n insighthub-dev --create-namespace \
  --force-conflicts

kubectl get pods -n insighthub-dev
```

### 8.2. Deploy vào EKS sau Terraform apply

```bash
aws eks update-kubeconfig \
  --region ap-southeast-1 \
  --name insighthub-dev-eks \
  --alias insighthub-dev

DB_ENDPOINT=$(terraform -chdir=infra output -raw db_endpoint)
DB_PASSWORD=$(terraform -chdir=infra output -raw db_password)
REDIS_ENDPOINT=$(terraform -chdir=infra output -raw redis_endpoint)
REDIS_TOKEN=$(terraform -chdir=infra output -raw redis_auth_token)
IRSA_ROLE_ARN=$(terraform -chdir=infra output -raw irsa_role_arn)

helm upgrade --install insighthub infra/helm/insighthub \
  -n insighthub-dev --create-namespace \
  -f infra/helm/values-dev.yaml \
  --set api.irsa.roleArn="${IRSA_ROLE_ARN}" \
  --set db.host="${DB_ENDPOINT%:*}" \
  --set db.username="insighthub" \
  --set db.name="insighthub" \
  --set api.env.REDIS_URL="rediss://:${REDIS_TOKEN}@${REDIS_ENDPOINT}:6379" \
  --set worker.env.REDIS_URL="rediss://:${REDIS_TOKEN}@${REDIS_ENDPOINT}:6379"
```

### 8.3. Smoke test

```bash
kubectl rollout status deployment/api -n insighthub-dev
kubectl rollout status deployment/ingestion-worker -n insighthub-dev
kubectl get pods -n insighthub-dev

kubectl port-forward svc/api 8000:8000 -n insighthub-dev

curl http://localhost:8000/healthz
curl -X POST http://localhost:8000/documents \
  -F "file=@sample-docs/so-tay-van-hanh.md"
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"InsightHub co may thanh phan?"}'
```

---

## 9. Artifact Checklist

Mentor dùng checklist này để review:

```text
[ ] infra/main.tf, providers.tf, variables.tf, outputs.tf, backend.tf tồn tại
[ ] infra/modules/database, cache, networking, irsa có main/variables/outputs
[ ] terraform fmt -check -recursive pass
[ ] terraform validate pass
[ ] checkov no HIGH/CRITICAL
[ ] Rego policies có encryption/no-public/tags
[ ] .github/workflows/iac.yml có fmt/lint/security-scan/policy-check/plan/cost/apply
[ ] GitHub Actions dùng OIDC, không long-lived AWS keys
[ ] policy-check/plan fail thật nếu AWS OIDC sai
[ ] kubectl get pods -n insighthub-dev: 5 workloads Running
[ ] smoke test có evidence
```

---

## 10. Troubleshooting Guide

### 10.1. `terraform init` backend fail

```text
Backend initialization required
```

Fix:

```bash
terraform init -reconfigure -backend-config=backend-dev.hcl
```

Nếu chỉ kiểm tra code local:

```bash
terraform init -backend=false
```

### 10.2. GitHub OIDC fail

**Triệu chứng 1:** `Error: Could not assume role with OIDC`

Chạy debug để xem claim thực tế:

```yaml
# Thêm vào job để xem JWT claims
- name: Debug OIDC token
  run: |
    curl -s -H "Authorization: bearer ${ACTIONS_ID_TOKEN_REQUEST_TOKEN}" \
      "${ACTIONS_ID_TOKEN_REQUEST_URL}&audience=sts.amazonaws.com" | \
      python3 -c "import sys,json,base64; t=json.load(sys.stdin)['value'].split('.')[1]; \
        print(json.dumps(json.loads(base64.b64decode(t+'==').decode()),indent=2))"
```

Kiểm tra lần lượt:

1. Secret `AWS_OIDC_ROLE_ARN` đã set chưa → `gh secret list`
2. Trust policy `sub` có match không → compare claim `sub` từ debug step với trust policy
3. OIDC provider ARN trong trust policy có đúng account ID không
4. Workflow có `permissions: id-token: write` ở job level không
5. IAM role session duration (`--max-session-duration`) phải ≥ workflow runtime

**Triệu chứng 2:** `403 Forbidden` khi Terraform plan gọi AWS API

```bash
# Kiểm tra role có policy đủ quyền chưa
aws iam list-attached-role-policies --role-name insighthub-github-actions
aws iam simulate-principal-policy \
  --policy-source-arn "arn:aws:iam::${AWS_ACCOUNT}:role/insighthub-github-actions" \
  --action-names "eks:DescribeCluster" "rds:CreateDBInstance" "ec2:DescribeVpcs" \
  --query 'EvaluationResults[].EvalDecision'
```

**Triệu chứng 3:** Environment protection rule block apply

```text
Deployment request pending approval
```

→ Đây là expected behavior — reviewer cần approve trên GitHub UI tại `Actions → workflow run → Review deployments`.

### 10.3. Checkov fail nhiều HIGH

Xử lý theo nhóm:

```bash
checkov -d infra --quiet
```

Ưu tiên:

1. Public exposure.
2. Encryption.
3. Secrets.
4. Logging.
5. Tagging.

Skip check chỉ khi có rationale trong `.checkov.yaml`.

### 10.4. TFLint plugin handshake trên macOS

Triệu chứng:

```text
Failed to initialize plugins; Unrecognized remote plugin message
```

Fix nhanh:

```bash
brew reinstall tflint
rm -rf ~/.tflint.d/plugins
tflint --init
tflint --recursive
```

Nếu vẫn lỗi, dùng GitHub Actions/Linux runner làm source of truth cho Day 3 lint evidence.

### 10.5. Helm upgrade conflict với `kubectl set env`

Nếu Day 2 demo để lại manager `kubectl-set`:

```bash
helm upgrade --install insighthub infra/helm/insighthub \
  -f infra/helm/values-dev.yaml \
  -n insighthub-dev --create-namespace \
  --force-conflicts
```

### 10.6. Postgres probe spam `$(POSTGRES_USER)`

Probe phải chạy qua shell nếu cần env expansion:

```yaml
command: ["/bin/sh", "-c", "exec pg_isready -U \"$POSTGRES_USER\" -h 127.0.0.1 -p 5432"]
```

---

## 11. Q&A Bank

**Q: Vì sao không dùng IAM user trong pod?**  
A: IAM user là long-lived credential. IRSA dùng OIDC, scope theo ServiceAccount và rotate tự nhiên qua AWS STS.

**Q: Vì sao RDS/Redis dùng managed services thay vì StatefulSet?**  
A: Day 3 mục tiêu là production-grade cloud posture: backup, encryption, patching, HA path, monitoring. StatefulSet tự quản lý phù hợp khi có yêu cầu vận hành riêng.

**Q: Vì sao `apply` cần manual approval?**  
A: Terraform có blast radius lớn. Plan phải được review trước khi tạo/sửa/xóa cloud resource.

**Q: Checkov skip có phải gian lận không?**  
A: Không, nếu skip có rationale rõ và không che HIGH critical risk thật. Skip không được dùng để né public DB, plaintext secret, hoặc disabled encryption.

**Q: Infracost vượt $50 thì làm gì?**  
A: Giảm node desired size, dùng single NAT gateway cho dev, giảm RDS class/storage, hoặc dùng minikube fallback cho demo.

