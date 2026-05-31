# ═══════════════════════════════════════════════════════════════════════════
# InsightHub — Infrastructure Root Module
# Provisions: VPC → EKS → RDS (PostgreSQL + pgvector) → ElastiCache Redis
#             → K8s namespace → IRSA role
# ═══════════════════════════════════════════════════════════════════════════

# ── VPC ──────────────────────────────────────────────────────────────────────

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.16"

  name = "${local.name_prefix}-vpc"
  cidr = var.vpc_cidr

  azs              = var.availability_zones
  public_subnets   = local.public_subnets
  private_subnets  = local.private_subnets
  database_subnets = local.db_subnets

  enable_nat_gateway           = true
  single_nat_gateway           = var.environment == "dev" # save cost in dev
  enable_dns_hostnames         = true
  enable_dns_support           = true
  create_database_subnet_group = true

  # EKS requires these subnet tags for load-balancer discovery
  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }

  tags = local.common_tags
}

# ── EKS ──────────────────────────────────────────────────────────────────────

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.31"

  cluster_name    = "${local.name_prefix}-eks"
  cluster_version = var.eks_cluster_version

  cluster_endpoint_public_access       = true
  cluster_endpoint_private_access      = true
  cluster_endpoint_public_access_cidrs = ["0.0.0.0/0"] # tighten in prod

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Encrypt secrets at rest with a managed key
  cluster_encryption_config = {
    resources = ["secrets"]
  }

  # Enable control-plane logging
  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # OIDC provider — required for IRSA
  enable_irsa = true

  eks_managed_node_groups = {
    default = {
      instance_types = [var.eks_node_instance_type]
      min_size       = var.eks_node_min_size
      max_size       = var.eks_node_max_size
      desired_size   = var.eks_node_desired_size

      labels = {
        role = "application"
      }
    }
  }

  tags = local.common_tags
}

# ── Kubernetes namespace ───────────────────────────────────────────────────────

resource "kubernetes_namespace" "insighthub" {
  metadata {
    name = "${var.project_name}-${var.environment}"

    labels = {
      project     = var.project_name
      environment = var.environment
      managed_by  = "terraform"
    }
  }

  depends_on = [module.eks]
}

# ── KMS Keys ─────────────────────────────────────────────────────────────────

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

resource "aws_kms_key" "secrets" {
  description             = "KMS key for InsightHub Secrets Manager"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowRootAccount"
        Effect = "Allow"
        Principal = {
          AWS = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${local.name_prefix}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

resource "aws_kms_key" "rds" {
  description             = "KMS key for InsightHub RDS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowRootAccount"
        Effect = "Allow"
        Principal = {
          AWS = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowRDSEncryption"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
        Action   = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${local.name_prefix}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

resource "aws_kms_key" "elasticache" {
  description             = "KMS key for InsightHub ElastiCache encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowRootAccount"
        Effect = "Allow"
        Principal = {
          AWS = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_kms_alias" "elasticache" {
  name          = "alias/${local.name_prefix}-elasticache"
  target_key_id = aws_kms_key.elasticache.key_id
}

# ── Security Groups ───────────────────────────────────────────────────────────

module "security_groups" {
  source = "./modules/networking"

  name_prefix    = local.name_prefix
  vpc_id         = module.vpc.vpc_id
  eks_node_sg_id = module.eks.node_security_group_id
  tags           = local.common_tags
}

# ── Data Services ─────────────────────────────────────────────────────────────

module "database" {
  source = "./modules/database"

  name_prefix            = local.name_prefix
  environment            = var.environment
  db_name                = var.db_name
  db_username            = var.db_username
  db_instance_class      = var.db_instance_class
  db_allocated_storage   = var.db_allocated_storage
  db_multi_az            = var.db_multi_az
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [module.security_groups.rds_sg_id]
  rds_kms_key_arn        = aws_kms_key.rds.arn
  secrets_kms_key_arn    = aws_kms_key.secrets.arn
  tags                   = local.common_tags
}

module "cache" {
  source = "./modules/cache"

  name_prefix             = local.name_prefix
  environment             = var.environment
  redis_node_type         = var.redis_node_type
  redis_num_cache_nodes   = var.redis_num_cache_nodes
  subnet_ids              = module.vpc.private_subnets
  security_group_ids      = [module.security_groups.redis_sg_id]
  elasticache_kms_key_arn = aws_kms_key.elasticache.arn
  secrets_kms_key_arn     = aws_kms_key.secrets.arn
  tags                    = local.common_tags
}

# ── IRSA — Pod IAM Role ───────────────────────────────────────────────────────

module "irsa" {
  source = "./modules/irsa"

  cluster_oidc_issuer_url = module.eks.cluster_oidc_issuer_url
  namespace               = kubernetes_namespace.insighthub.metadata[0].name
  service_account_name    = "insighthub-api"
  name_prefix             = local.name_prefix
  secret_arns             = [module.database.db_secret_arn, module.cache.redis_auth_token_secret_arn]
  kms_key_arns            = [aws_kms_key.secrets.arn]
  tags                    = local.common_tags
}
