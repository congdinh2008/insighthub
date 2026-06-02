#!/usr/bin/env bash
# =============================================================================
# InsightHub — AWS Setup Script (Day 3 prerequisites)
# Tạo hoặc xóa toàn bộ AWS resources cần thiết cho Terraform backend + GitHub OIDC.
#
# Usage:
#   bash scripts/setup-aws.sh                     # tạo với defaults
#   bash scripts/setup-aws.sh --env staging        # staging environment
#   bash scripts/setup-aws.sh --policy production  # scoped IAM policy (thay vì AdministratorAccess)
#   bash scripts/setup-aws.sh --skip-github        # bỏ qua bước set GitHub secret
#   bash scripts/setup-aws.sh --destroy            # xóa toàn bộ resources
#   bash scripts/setup-aws.sh --destroy --env staging
#
# Idempotent: chạy nhiều lần không tạo duplicate.
# =============================================================================

set -euo pipefail

# ── Màu sắc ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
step()    { echo -e "\n${BOLD}${CYAN}━━ $* ━━${NC}"; }
die()     { error "$*"; exit 1; }

# ── Defaults ─────────────────────────────────────────────────────────────────
ENV="dev"
AWS_REGION="${AWS_REGION:-ap-southeast-1}"
GITHUB_ORG="${GITHUB_ORG:-congdinh2008}"
GITHUB_REPO="${GITHUB_REPO:-insighthub}"
IAM_ROLE_NAME="insighthub-github-actions"
IAM_POLICY_TYPE="lab"      # lab | production
SKIP_GITHUB=false
DESTROY=false
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Parse arguments ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)         ENV="$2"; shift 2 ;;
    --policy)      IAM_POLICY_TYPE="$2"; shift 2 ;;
    --skip-github) SKIP_GITHUB=true; shift ;;
    --destroy)     DESTROY=true; shift ;;
    --region)      AWS_REGION="$2"; shift 2 ;;
    --org)         GITHUB_ORG="$2"; shift 2 ;;
    --repo)        GITHUB_REPO="$2"; shift 2 ;;
    --help|-h)
      # In phần header docstring (từ dòng 2 đến dòng trước set -euo pipefail)
      awk '/^# ===/{p=1} p{sub(/^# ?/,""); print} /^set -euo/{exit}' "$0"
      exit 0 ;;
    *) die "Unknown argument: $1. Use --help." ;;
  esac
done

# ── Derived variables ─────────────────────────────────────────────────────────
TF_BUCKET="insighthub-tfstate-${ENV}"
TF_BUCKET_LOGS="insighthub-tfstate-${ENV}-logs"
TF_LOCK_TABLE="insighthub-tflock-${ENV}"
CUSTOM_POLICY_NAME="insighthub-github-actions-policy"
OIDC_URL="token.actions.githubusercontent.com"

# ── Prerequisites check ───────────────────────────────────────────────────────
check_prereqs() {
  step "Kiểm tra prerequisites"
  local missing=()
  command -v aws  >/dev/null 2>&1 || missing+=("aws-cli")
  command -v jq   >/dev/null 2>&1 || missing+=("jq")
  [ ${#missing[@]} -gt 0 ] && die "Thiếu: ${missing[*]}. Cài đặt trước khi tiếp tục."
  ok "aws-cli, jq — OK"

  AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) \
    || die "Không lấy được AWS account ID. Kiểm tra credentials: aws configure"
  CALLER=$(aws sts get-caller-identity --query Arn --output text)
  ok "AWS Account: ${AWS_ACCOUNT} (${CALLER})"
  ok "Region     : ${AWS_REGION}"

  if [ "$SKIP_GITHUB" = false ]; then
    command -v gh >/dev/null 2>&1 || { warn "gh CLI không tìm thấy — bỏ qua bước set GitHub secret (--skip-github)"; SKIP_GITHUB=true; }
    if [ "$SKIP_GITHUB" = false ]; then
      gh auth status >/dev/null 2>&1 || { warn "gh chưa auth — bỏ qua bước set GitHub secret"; SKIP_GITHUB=true; }
    fi
  fi
}

# ═════════════════════════════════════════════════════════════════════════════
# SETUP
# ═════════════════════════════════════════════════════════════════════════════

setup() {
  echo -e "\n${BOLD}InsightHub AWS Setup — environment: ${CYAN}${ENV}${NC}${BOLD}, region: ${CYAN}${AWS_REGION}${NC}"
  echo -e "  Terraform bucket : s3://${TF_BUCKET}"
  echo -e "  DynamoDB table   : ${TF_LOCK_TABLE}"
  echo -e "  IAM Role         : ${IAM_ROLE_NAME}"
  echo -e "  Policy type      : ${IAM_POLICY_TYPE}"
  echo -e "  GitHub repo      : ${GITHUB_ORG}/${GITHUB_REPO}"

  # ── Bước 1: S3 logs bucket ─────────────────────────────────────────────────
  step "1/7  S3 Access Logs Bucket"
  if aws s3api head-bucket --bucket "$TF_BUCKET_LOGS" 2>/dev/null; then
    ok "s3://${TF_BUCKET_LOGS} đã tồn tại — bỏ qua"
  else
    if [ "$AWS_REGION" = "us-east-1" ]; then
      aws s3api create-bucket --bucket "$TF_BUCKET_LOGS" --region "$AWS_REGION" >/dev/null
    else
      aws s3api create-bucket --bucket "$TF_BUCKET_LOGS" --region "$AWS_REGION" \
        --create-bucket-configuration LocationConstraint="$AWS_REGION" >/dev/null
    fi
    # Block public access on logs bucket
    aws s3api put-public-access-block --bucket "$TF_BUCKET_LOGS" \
      --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
    ok "s3://${TF_BUCKET_LOGS} — created"
  fi

  # ── Bước 2: S3 state bucket ────────────────────────────────────────────────
  step "2/7  S3 Terraform State Bucket"
  if aws s3api head-bucket --bucket "$TF_BUCKET" 2>/dev/null; then
    ok "s3://${TF_BUCKET} đã tồn tại — kiểm tra cấu hình"
  else
    if [ "$AWS_REGION" = "us-east-1" ]; then
      aws s3api create-bucket --bucket "$TF_BUCKET" --region "$AWS_REGION" >/dev/null
    else
      aws s3api create-bucket --bucket "$TF_BUCKET" --region "$AWS_REGION" \
        --create-bucket-configuration LocationConstraint="$AWS_REGION" >/dev/null
    fi
    ok "s3://${TF_BUCKET} — created"
  fi

  # Versioning
  VERSIONING=$(aws s3api get-bucket-versioning --bucket "$TF_BUCKET" \
    --query 'Status' --output text 2>/dev/null || echo "")
  if [ "$VERSIONING" != "Enabled" ]; then
    aws s3api put-bucket-versioning --bucket "$TF_BUCKET" \
      --versioning-configuration Status=Enabled
    ok "Versioning — enabled"
  else
    ok "Versioning — already enabled"
  fi

  # Block public access
  aws s3api put-public-access-block --bucket "$TF_BUCKET" \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  ok "Public access — blocked"

  # Encryption
  aws s3api put-bucket-encryption --bucket "$TF_BUCKET" \
    --server-side-encryption-configuration '{
      "Rules": [{
        "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
        "BucketKeyEnabled": true
      }]
    }'
  ok "Encryption — AES256 enabled"

  # Access logging
  aws s3api put-bucket-logging --bucket "$TF_BUCKET" \
    --bucket-logging-status "{
      \"LoggingEnabled\": {
        \"TargetBucket\": \"${TF_BUCKET_LOGS}\",
        \"TargetPrefix\": \"tfstate-access/\"
      }
    }" 2>/dev/null || warn "Access logging: có thể cần ACLs — bỏ qua nếu dùng Object Ownership=BucketOwnerEnforced"
  ok "Access logging — configured"

  # ── Bước 3: DynamoDB ───────────────────────────────────────────────────────
  step "3/7  DynamoDB State Lock Table"
  TABLE_STATUS=$(aws dynamodb describe-table --table-name "$TF_LOCK_TABLE" \
    --region "$AWS_REGION" --query 'Table.TableStatus' --output text 2>/dev/null || echo "NOT_FOUND")

  if [ "$TABLE_STATUS" = "NOT_FOUND" ]; then
    aws dynamodb create-table \
      --table-name "$TF_LOCK_TABLE" \
      --attribute-definitions AttributeName=LockID,AttributeType=S \
      --key-schema AttributeName=LockID,KeyType=HASH \
      --billing-mode PAY_PER_REQUEST \
      --region "$AWS_REGION" >/dev/null

    # Chờ table active
    info "Chờ DynamoDB table active..."
    aws dynamodb wait table-exists --table-name "$TF_LOCK_TABLE" --region "$AWS_REGION"
    ok "${TF_LOCK_TABLE} — created"
  else
    ok "${TF_LOCK_TABLE} — already exists (${TABLE_STATUS})"
  fi

  # PITR
  aws dynamodb update-continuous-backups \
    --table-name "$TF_LOCK_TABLE" \
    --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
    --region "$AWS_REGION" >/dev/null
  ok "Point-in-Time Recovery — enabled"

  # ── Bước 4: OIDC Provider ──────────────────────────────────────────────────
  step "4/7  GitHub Actions OIDC Provider"
  OIDC_ARN=$(aws iam list-open-id-connect-providers \
    --query "OpenIDConnectProviderList[?contains(Arn,\`${OIDC_URL}\`)].Arn" \
    --output text 2>/dev/null || echo "")

  if [ -n "$OIDC_ARN" ]; then
    ok "OIDC Provider đã tồn tại — ${OIDC_ARN}"
  else
    OIDC_ARN=$(aws iam create-open-id-connect-provider \
      --url "https://${OIDC_URL}" \
      --client-id-list sts.amazonaws.com \
      --thumbprint-list \
        6938fd4d98bab03faadb97b34396831e3780aea1 \
        1c58a3a8518e8759bf075b76b750d4f2df264fcd \
      --query 'OpenIDConnectProviderArn' --output text)
    ok "OIDC Provider — created: ${OIDC_ARN}"
  fi

  # ── Bước 5: IAM Trust Policy ───────────────────────────────────────────────
  step "5/7  IAM Role (GitHub Actions)"
  TRUST_POLICY=$(cat <<TRUST
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GitHubActionsOIDC",
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${AWS_ACCOUNT}:oidc-provider/${OIDC_URL}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_URL}:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "${OIDC_URL}:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
TRUST
)

  ROLE_EXISTS=$(aws iam get-role --role-name "$IAM_ROLE_NAME" \
    --query 'Role.Arn' --output text 2>/dev/null || echo "")

  if [ -n "$ROLE_EXISTS" ]; then
    ok "IAM Role đã tồn tại — ${ROLE_EXISTS}"
    # Cập nhật trust policy (phòng khi repo/org thay đổi)
    aws iam update-assume-role-policy \
      --role-name "$IAM_ROLE_NAME" \
      --policy-document "$TRUST_POLICY" >/dev/null
    ok "Trust policy — updated"
    OIDC_ROLE_ARN="$ROLE_EXISTS"
  else
    OIDC_ROLE_ARN=$(aws iam create-role \
      --role-name "$IAM_ROLE_NAME" \
      --assume-role-policy-document "$TRUST_POLICY" \
      --description "GitHub Actions OIDC role for InsightHub IaC pipeline" \
      --max-session-duration 3600 \
      --query 'Role.Arn' --output text)
    ok "IAM Role — created: ${OIDC_ROLE_ARN}"
  fi

  # ── Bước 6: IAM Policy ────────────────────────────────────────────────────
  step "6/7  IAM Policy"
  if [ "$IAM_POLICY_TYPE" = "lab" ]; then
    # AdministratorAccess — đủ cho lab
    ALREADY=$(aws iam list-attached-role-policies --role-name "$IAM_ROLE_NAME" \
      --query 'AttachedPolicies[?PolicyName==`AdministratorAccess`].PolicyName' \
      --output text 2>/dev/null || echo "")
    if [ -n "$ALREADY" ]; then
      ok "AdministratorAccess — already attached"
    else
      aws iam attach-role-policy \
        --role-name "$IAM_ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/AdministratorAccess"
      ok "AdministratorAccess — attached (lab mode)"
    fi
    warn "Lab mode: AdministratorAccess — dùng --policy production cho scoped policy"
  else
    # Scoped policy cho production
    CUSTOM_POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT}:policy/${CUSTOM_POLICY_NAME}"
    POLICY_EXISTS=$(aws iam get-policy --policy-arn "$CUSTOM_POLICY_ARN" \
      --query 'Policy.Arn' --output text 2>/dev/null || echo "")

    SCOPED_POLICY=$(cat <<'POLICY'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CoreInfra",
      "Effect": "Allow",
      "Action": [
        "ec2:*", "eks:*", "rds:*", "elasticache:*",
        "kms:*", "secretsmanager:*", "iam:*",
        "logs:*", "cloudwatch:*", "s3:*", "dynamodb:*",
        "autoscaling:*", "elb:*", "elasticloadbalancing:*",
        "ecr:*", "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
POLICY
)
    if [ -n "$POLICY_EXISTS" ]; then
      # Update existing policy
      VERSION_ID=$(aws iam list-policy-versions \
        --policy-arn "$CUSTOM_POLICY_ARN" \
        --query 'Versions[?IsDefaultVersion==`false`].VersionId | [0]' \
        --output text 2>/dev/null || echo "")
      [ -n "$VERSION_ID" ] && [ "$VERSION_ID" != "None" ] && \
        aws iam delete-policy-version --policy-arn "$CUSTOM_POLICY_ARN" --version-id "$VERSION_ID" 2>/dev/null || true
      aws iam create-policy-version \
        --policy-arn "$CUSTOM_POLICY_ARN" \
        --policy-document "$SCOPED_POLICY" \
        --set-as-default >/dev/null
      ok "${CUSTOM_POLICY_NAME} — updated"
    else
      CUSTOM_POLICY_ARN=$(aws iam create-policy \
        --policy-name "$CUSTOM_POLICY_NAME" \
        --policy-document "$SCOPED_POLICY" \
        --description "Scoped IAM policy for InsightHub GitHub Actions IaC pipeline" \
        --query 'Policy.Arn' --output text)
      ok "${CUSTOM_POLICY_NAME} — created"
    fi

    ALREADY=$(aws iam list-attached-role-policies --role-name "$IAM_ROLE_NAME" \
      --query "AttachedPolicies[?PolicyArn==\`${CUSTOM_POLICY_ARN}\`].PolicyName" \
      --output text 2>/dev/null || echo "")
    if [ -z "$ALREADY" ]; then
      aws iam attach-role-policy \
        --role-name "$IAM_ROLE_NAME" \
        --policy-arn "$CUSTOM_POLICY_ARN"
      ok "${CUSTOM_POLICY_NAME} — attached"
    else
      ok "${CUSTOM_POLICY_NAME} — already attached"
    fi
  fi

  # ── Bước 7: GitHub Secret + backend.hcl ───────────────────────────────────
  step "7/7  GitHub Secret + backend-${ENV}.hcl"

  if [ "$SKIP_GITHUB" = false ]; then
    gh secret set AWS_OIDC_ROLE_ARN \
      --body "$OIDC_ROLE_ARN" \
      --repo "${GITHUB_ORG}/${GITHUB_REPO}" 2>/dev/null && \
      ok "GitHub secret AWS_OIDC_ROLE_ARN — set on ${GITHUB_ORG}/${GITHUB_REPO}" || \
      warn "Không set được GitHub secret — set thủ công: AWS_OIDC_ROLE_ARN=${OIDC_ROLE_ARN}"
  else
    warn "Bỏ qua GitHub secret (--skip-github). Set thủ công:"
    echo "  gh secret set AWS_OIDC_ROLE_ARN --body \"${OIDC_ROLE_ARN}\" --repo ${GITHUB_ORG}/${GITHUB_REPO}"
  fi

  # Cập nhật backend-ENV.hcl
  BACKEND_FILE="${REPO_ROOT}/infra/backend-${ENV}.hcl"
  cat > "$BACKEND_FILE" <<BACKEND
bucket         = "${TF_BUCKET}"
key            = "insighthub/${ENV}/terraform.tfstate"
region         = "${AWS_REGION}"
encrypt        = true
dynamodb_table = "${TF_LOCK_TABLE}"
BACKEND
  ok "infra/backend-${ENV}.hcl — updated"

  # ── Summary ───────────────────────────────────────────────────────────────
  echo -e "\n${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BOLD}${GREEN}  ✅  InsightHub AWS Setup hoàn thành!${NC}"
  echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo
  echo -e "  ${CYAN}S3 state bucket  :${NC} s3://${TF_BUCKET}"
  echo -e "  ${CYAN}S3 logs bucket   :${NC} s3://${TF_BUCKET_LOGS}"
  echo -e "  ${CYAN}DynamoDB table   :${NC} ${TF_LOCK_TABLE} (${AWS_REGION})"
  echo -e "  ${CYAN}OIDC Provider    :${NC} ${OIDC_ARN}"
  echo -e "  ${CYAN}IAM Role ARN     :${NC} ${OIDC_ROLE_ARN}"
  echo -e "  ${CYAN}backend HCL      :${NC} infra/backend-${ENV}.hcl"
  echo
  echo -e "  ${BOLD}Bước tiếp theo:${NC}"
  echo -e "  1. cd infra && terraform init -backend-config=backend-${ENV}.hcl"
  echo -e "  2. terraform plan -var=\"environment=${ENV}\""
  echo -e "  3. Merge PR → GitHub Actions pipeline sẽ dùng OIDC tự động"
  echo
}

# ═════════════════════════════════════════════════════════════════════════════
# DESTROY
# ═════════════════════════════════════════════════════════════════════════════

destroy() {
  echo -e "\n${BOLD}${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BOLD}${RED}  ⚠️   InsightHub AWS DESTROY — environment: ${ENV}${NC}"
  echo -e "${BOLD}${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo
  echo -e "  Sẽ xóa:"
  echo -e "  ${RED}✗${NC} s3://${TF_BUCKET}"
  echo -e "  ${RED}✗${NC} s3://${TF_BUCKET_LOGS}"
  echo -e "  ${RED}✗${NC} DynamoDB: ${TF_LOCK_TABLE}"
  echo -e "  ${RED}✗${NC} IAM Role: ${IAM_ROLE_NAME}"
  echo -e "  ${YELLOW}⚡${NC} OIDC Provider: KHÔNG xóa (shared resource)"
  echo
  read -r -p "Xác nhận xóa? [yes/N] " CONFIRM
  [[ "$CONFIRM" == "yes" ]] || { info "Hủy."; exit 0; }

  # IAM Role
  step "IAM Role"
  if aws iam get-role --role-name "$IAM_ROLE_NAME" >/dev/null 2>&1; then
    # Detach all policies
    POLICIES=$(aws iam list-attached-role-policies --role-name "$IAM_ROLE_NAME" \
      --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null || echo "")
    for ARN in $POLICIES; do
      aws iam detach-role-policy --role-name "$IAM_ROLE_NAME" --policy-arn "$ARN"
      ok "Detached: $ARN"
    done
    # Delete inline policies
    INLINE=$(aws iam list-role-policies --role-name "$IAM_ROLE_NAME" \
      --query 'PolicyNames[]' --output text 2>/dev/null || echo "")
    for POL in $INLINE; do
      aws iam delete-role-policy --role-name "$IAM_ROLE_NAME" --policy-name "$POL"
    done
    aws iam delete-role --role-name "$IAM_ROLE_NAME"
    ok "IAM Role ${IAM_ROLE_NAME} — deleted"
  else
    ok "IAM Role ${IAM_ROLE_NAME} — không tồn tại, bỏ qua"
  fi

  # Custom policy
  CUSTOM_POLICY_ARN="arn:aws:iam::${AWS_ACCOUNT}:policy/${CUSTOM_POLICY_NAME}"
  if aws iam get-policy --policy-arn "$CUSTOM_POLICY_ARN" >/dev/null 2>&1; then
    step "Custom IAM Policy"
    # Delete non-default versions
    VERSIONS=$(aws iam list-policy-versions --policy-arn "$CUSTOM_POLICY_ARN" \
      --query 'Versions[?IsDefaultVersion==`false`].VersionId' --output text 2>/dev/null || echo "")
    for VID in $VERSIONS; do
      aws iam delete-policy-version --policy-arn "$CUSTOM_POLICY_ARN" --version-id "$VID"
    done
    aws iam delete-policy --policy-arn "$CUSTOM_POLICY_ARN"
    ok "Custom policy ${CUSTOM_POLICY_NAME} — deleted"
  fi

  # DynamoDB
  step "DynamoDB"
  if aws dynamodb describe-table --table-name "$TF_LOCK_TABLE" \
    --region "$AWS_REGION" >/dev/null 2>&1; then
    aws dynamodb delete-table --table-name "$TF_LOCK_TABLE" --region "$AWS_REGION" >/dev/null
    ok "DynamoDB ${TF_LOCK_TABLE} — deleted"
  else
    ok "DynamoDB ${TF_LOCK_TABLE} — không tồn tại, bỏ qua"
  fi

  # S3 buckets
  for BUCKET in "$TF_BUCKET" "$TF_BUCKET_LOGS"; do
    step "S3 s3://${BUCKET}"
    if ! aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
      ok "s3://${BUCKET} — không tồn tại, bỏ qua"
      continue
    fi

    # Xóa tất cả versions
    info "Xóa object versions..."
    aws s3api list-object-versions --bucket "$BUCKET" \
      --query '{Objects: Versions[].{Key:Key,VersionId:VersionId}}' \
      --output json 2>/dev/null | \
    python3 -c "
import sys, json, boto3
data = json.load(sys.stdin)
objs = data.get('Objects') or []
if objs:
    s3 = boto3.client('s3', region_name='${AWS_REGION}')
    s3.delete_objects(Bucket='${BUCKET}', Delete={'Objects': objs})
    print(f'  Deleted {len(objs)} versions')
" 2>/dev/null || true

    # Xóa delete markers
    aws s3api list-object-versions --bucket "$BUCKET" \
      --query '{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}' \
      --output json 2>/dev/null | \
    python3 -c "
import sys, json, boto3
data = json.load(sys.stdin)
objs = data.get('Objects') or []
if objs:
    s3 = boto3.client('s3', region_name='${AWS_REGION}')
    s3.delete_objects(Bucket='${BUCKET}', Delete={'Objects': objs})
    print(f'  Deleted {len(objs)} delete markers')
" 2>/dev/null || true

    # Xóa objects thường
    aws s3 rm "s3://${BUCKET}" --recursive --quiet 2>/dev/null || true

    # Xóa bucket
    aws s3api delete-bucket --bucket "$BUCKET" --region "$AWS_REGION"
    ok "s3://${BUCKET} — deleted"
  done

  echo -e "\n${GREEN}✅ Destroy hoàn thành.${NC}"
}

# ── Main ──────────────────────────────────────────────────────────────────────
check_prereqs
if [ "$DESTROY" = true ]; then
  destroy
else
  setup
fi
