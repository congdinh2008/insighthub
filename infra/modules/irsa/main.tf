terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }
}

variable "cluster_oidc_issuer_url" { type = string }
variable "namespace" { type = string }
variable "service_account_name" { type = string }
variable "name_prefix" { type = string }
variable "secret_arns" { type = list(string) }
variable "kms_key_arns" { type = list(string) }
variable "tags" { type = map(string) }

locals {
  oidc_url_stripped = replace(var.cluster_oidc_issuer_url, "https://", "")
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

# IRSA trust policy — only the specific ServiceAccount in the specific namespace can assume
data "aws_iam_policy_document" "irsa_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = ["arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${local.oidc_url_stripped}"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_url_stripped}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account_name}"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_url_stripped}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "irsa" {
  name               = "${var.name_prefix}-irsa-${var.service_account_name}"
  assume_role_policy = data.aws_iam_policy_document.irsa_assume.json

  tags = var.tags
}

# Least-privilege: only read secrets that InsightHub needs
data "aws_iam_policy_document" "irsa_permissions" {
  statement {
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ]
    resources = var.secret_arns
  }

  statement {
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = var.kms_key_arns
    condition {
      test     = "StringLike"
      variable = "kms:ViaService"
      values   = ["secretsmanager.*.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "irsa_permissions" {
  name   = "${var.name_prefix}-irsa-permissions"
  role   = aws_iam_role.irsa.id
  policy = data.aws_iam_policy_document.irsa_permissions.json
}

output "role_arn" {
  value = aws_iam_role.irsa.arn
}

output "role_name" {
  value = aws_iam_role.irsa.name
}
