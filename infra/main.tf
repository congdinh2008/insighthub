module "network" {
  source = "./modules/network"

  name                  = local.name
  vpc_cidr              = var.vpc_cidr
  availability_zone_ids = var.availability_zone_ids
  tags                  = local.common_tags
}

module "eks" {
  source = "./modules/eks"

  name                        = local.name
  kubernetes_version          = var.kubernetes_version
  private_subnet_ids          = module.network.private_subnet_ids
  admin_cidrs                 = var.admin_cidrs
  cluster_admin_principal_arn = var.cluster_admin_principal_arn
  node_instance_types         = var.node_instance_types
  node_desired_size           = var.node_desired_size
  tags                        = local.common_tags
}

module "database" {
  source = "./modules/database"

  name                  = local.name
  vpc_id                = module.network.vpc_id
  subnet_ids            = module.network.data_subnet_ids
  application_sg_id     = module.eks.node_security_group_id
  instance_class        = var.rds_instance_class
  backup_retention_days = var.database_backup_retention_days
  environment           = var.environment
  tags                  = local.common_tags
}

module "cache" {
  source = "./modules/cache"

  name              = local.name
  vpc_id            = module.network.vpc_id
  subnet_ids        = module.network.data_subnet_ids
  application_sg_id = module.eks.node_security_group_id
  node_type         = var.redis_node_type
  environment       = var.environment
  tags              = local.common_tags
}

module "registry" {
  source = "./modules/registry"

  name = local.name
  tags = local.common_tags
}

resource "aws_secretsmanager_secret" "application" {
  # checkov:skip=CKV2_AWS_57:The JSON contains provider-owned credentials with independent rotation; replacement is an approved pipeline operation.
  name                    = var.application_secret_name
  description             = "Runtime configuration for ${local.name}; value is populated outside Terraform."
  recovery_window_in_days = 7
  kms_key_id              = module.database.kms_key_arn

  tags = local.common_tags
}

data "aws_iam_policy_document" "application_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [module.eks.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${module.eks.oidc_issuer_hostpath}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${module.eks.oidc_issuer_hostpath}:sub"
      values   = ["system:serviceaccount:${local.name}:insighthub"]
    }
  }
}

resource "aws_iam_role" "application" {
  name               = "${local.name}-application"
  assume_role_policy = data.aws_iam_policy_document.application_assume_role.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "application_secret" {
  statement {
    sid       = "ReadApplicationSecret"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = [aws_secretsmanager_secret.application.arn]
  }

  statement {
    sid       = "DecryptApplicationSecret"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = [module.database.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "application_secret" {
  name   = "read-application-secret"
  role   = aws_iam_role.application.id
  policy = data.aws_iam_policy_document.application_secret.json
}

data "aws_iam_policy_document" "load_balancer_controller_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [module.eks.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${module.eks.oidc_issuer_hostpath}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${module.eks.oidc_issuer_hostpath}:sub"
      values   = ["system:serviceaccount:kube-system:aws-load-balancer-controller"]
    }
  }
}

resource "aws_iam_role" "load_balancer_controller" {
  name               = "${local.name}-load-balancer-controller"
  assume_role_policy = data.aws_iam_policy_document.load_balancer_controller_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "load_balancer_controller" {
  role       = aws_iam_role.load_balancer_controller.name
  policy_arn = var.load_balancer_controller_policy_arn
}

check "lab_expiry" {
  assert {
    condition     = timecmp(var.expires_at, timestamp()) > 0
    error_message = "expires_at must be in the future before planning a lab."
  }
}
