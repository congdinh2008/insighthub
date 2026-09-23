locals {
  tags = {
    project     = "insighthub"
    environment = "bootstrap"
    owner       = var.owner
    cost_center = var.cost_center
    managed_by  = "terraform"
    Class       = "DO2603"
    LabId       = var.lab_id
    ExpiresAt   = var.expires_at
  }
}

resource "aws_kms_key" "state" {
  # checkov:skip=CKV2_AWS_64:AWS installs its account-scoped default key policy; administration remains with delegated account roles.
  description             = "Encrypt InsightHub Terraform state"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = local.tags
}

resource "aws_s3_bucket" "state" {
  # checkov:skip=CKV2_AWS_62:Terraform state has no event-driven consumer.
  # checkov:skip=CKV_AWS_18:CloudTrail is the audit source; a second logging bucket adds recursive state and cost to this lab.
  # checkov:skip=CKV_AWS_144:Cross-region replication is outside the short-lived single-region lab recovery objective.
  bucket = var.state_bucket_name
  tags   = local.tags
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    id     = "state-history"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.state.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = data.aws_iam_policy_document.state_bucket.json
}

data "aws_iam_policy_document" "state_bucket" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.state.arn,
      "${aws_s3_bucket.state.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
  tags            = local.tags
}

# These account-scoped service roles are prerequisites for a fresh lab account.
# Bootstrap owns only the roles that this project creates and removes them last.
resource "aws_iam_service_linked_role" "elasticache" {
  aws_service_name = "elasticache.amazonaws.com"
  description      = "Service-linked role for the InsightHub ElastiCache lab."
}

resource "aws_iam_service_linked_role" "rds" {
  aws_service_name = "rds.amazonaws.com"
  description      = "Service-linked role for the InsightHub RDS lab."
}

resource "aws_iam_service_linked_role" "eks" {
  aws_service_name = "eks.amazonaws.com"
  description      = "Service-linked role for the InsightHub EKS lab."
}

resource "aws_iam_service_linked_role" "eks_nodegroup" {
  aws_service_name = "eks-nodegroup.amazonaws.com"
  description      = "Service-linked role for the InsightHub EKS managed node group."
}

resource "aws_iam_service_linked_role" "elastic_load_balancing" {
  aws_service_name = "elasticloadbalancing.amazonaws.com"
  description      = "Service-linked role for the InsightHub ALB lab."
}

data "aws_iam_policy_document" "github_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:environment:${var.github_environment}"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name                 = "insighthub-${replace(var.github_environment, "insighthub-", "")}-github-apply"
  assume_role_policy   = data.aws_iam_policy_document.github_assume.json
  max_session_duration = 3600
  tags                 = local.tags
}

resource "aws_iam_role_policy_attachment" "github_deploy" {
  role       = aws_iam_role.github_deploy.name
  policy_arn = var.deployment_policy_arn
}

data "aws_iam_policy_document" "github_plan_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:environment:${var.github_plan_environment}"]
    }
  }
}

resource "aws_iam_role" "github_plan" {
  name                 = "insighthub-${replace(var.github_plan_environment, "insighthub-", "")}-github-plan"
  assume_role_policy   = data.aws_iam_policy_document.github_plan_assume.json
  max_session_duration = 3600
  tags                 = local.tags
}

resource "aws_iam_role_policy_attachment" "github_plan" {
  role       = aws_iam_role.github_plan.name
  policy_arn = var.plan_policy_arn
}

data "aws_iam_policy_document" "state_access" {
  statement {
    sid       = "ListStatePrefix"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.state.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["insighthub/*", "env:/*/insighthub/*"]
    }
  }

  statement {
    sid       = "ReadWriteStateAndLock"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.state.arn}/insighthub/*", "${aws_s3_bucket.state.arn}/env:/*/insighthub/*"]
  }

  statement {
    sid       = "DeleteLockOnly"
    effect    = "Allow"
    actions   = ["s3:DeleteObject"]
    resources = ["${aws_s3_bucket.state.arn}/insighthub/*.tflock", "${aws_s3_bucket.state.arn}/env:/*/insighthub/*.tflock"]
  }

  statement {
    sid       = "UseStateKey"
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
    resources = [aws_kms_key.state.arn]
  }

  statement {
    sid       = "ManageReviewedPlans"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.state.arn}/plans/*"]
  }
}

resource "aws_iam_role_policy" "state_access_apply" {
  name   = "terraform-state-access"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.state_access.json
}

data "aws_iam_policy_document" "state_read" {
  statement {
    sid       = "ListStatePrefix"
    effect    = "Allow"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.state.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["insighthub/*", "env:/*/insighthub/*"]
    }
  }

  statement {
    sid       = "ReadState"
    effect    = "Allow"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.state.arn}/insighthub/*", "${aws_s3_bucket.state.arn}/env:/*/insighthub/*"]
  }

  statement {
    sid       = "ManagePlanLock"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.state.arn}/insighthub/*.tflock", "${aws_s3_bucket.state.arn}/env:/*/insighthub/*.tflock"]
  }

  statement {
    sid       = "StoreReviewedPlan"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.state.arn}/plans/*"]
  }

  statement {
    sid       = "DecryptState"
    effect    = "Allow"
    actions   = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
    resources = [aws_kms_key.state.arn]
  }
}

resource "aws_iam_role_policy" "state_access_plan" {
  name   = "terraform-state-read"
  role   = aws_iam_role.github_plan.id
  policy = data.aws_iam_policy_document.state_read.json
}

check "lab_expiry" {
  assert {
    condition     = timecmp(var.expires_at, timestamp()) > 0
    error_message = "expires_at must be in the future."
  }
}
