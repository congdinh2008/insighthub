locals {
  required_tags = merge(var.additional_tags, {
    project     = var.project
    environment = var.environment
    owner       = var.owner
    cost_center = var.cost_center
    managed_by  = "terraform"
  })
}

module "network" {
  source = "./modules/network"

  name_prefix     = "${var.project}-${var.environment}"
  vpc_cidr        = var.vpc_cidr
  private_subnets = var.private_subnets
  tags            = local.required_tags
}

module "eks" {
  source = "./modules/eks"

  cluster_name       = var.cluster_name
  kubernetes_version = var.kubernetes_version
  private_subnet_ids = module.network.private_subnet_ids
  instance_types     = var.eks_node_instance_types
  desired_size       = var.eks_node_desired_size
  min_size           = var.eks_node_min_size
  max_size           = var.eks_node_max_size
  tags               = local.required_tags
}

module "rds" {
  source = "./modules/rds"

  name_prefix        = "${var.project}-${var.environment}"
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
  allowed_security_groups = {
    eks_cluster = module.eks.cluster_security_group_id
  }
  instance_class    = var.rds_instance_class
  allocated_storage = var.rds_allocated_storage
  engine_version    = var.rds_engine_version
  database_name     = var.rds_database_name
  master_username   = var.rds_master_username
  tags              = local.required_tags
}

module "redis" {
  source = "./modules/redis"

  name_prefix        = "${var.project}-${var.environment}"
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
  allowed_security_groups = {
    eks_cluster = module.eks.cluster_security_group_id
  }
  node_type      = var.redis_node_type
  engine_version = var.redis_engine_version
  tags           = local.required_tags
}

module "irsa" {
  source = "./modules/irsa"

  role_name       = "${var.project}-${var.environment}-insighthub"
  oidc_issuer_url = module.eks.oidc_issuer_url
  namespace       = "insighthub-dev"
  service_account = "insighthub"
  tags            = local.required_tags
}

resource "kubernetes_namespace_v1" "insighthub_dev" {
  metadata {
    name = "insighthub-dev"
    labels = {
      project     = var.project
      environment = var.environment
      managed_by  = "terraform"
    }
  }

  depends_on = [module.eks]
}

resource "kubernetes_service_account_v1" "insighthub" {
  metadata {
    name      = "insighthub"
    namespace = kubernetes_namespace_v1.insighthub_dev.metadata[0].name
    annotations = {
      "eks.amazonaws.com/role-arn" = module.irsa.role_arn
    }
  }
}
