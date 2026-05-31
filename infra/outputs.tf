output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS API server endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_oidc_provider_arn" {
  description = "OIDC provider ARN (used by IRSA)"
  value       = module.eks.oidc_provider_arn
}

output "k8s_namespace" {
  description = "Kubernetes namespace for InsightHub"
  value       = kubernetes_namespace.insighthub.metadata[0].name
}

output "db_endpoint" {
  description = "RDS endpoint (host:port)"
  value       = module.database.db_endpoint
}

output "db_name" {
  description = "PostgreSQL database name"
  value       = module.database.db_name
}

output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint"
  value       = module.cache.redis_endpoint
}

output "irsa_role_arn" {
  description = "IAM Role ARN for IRSA — annotate K8s ServiceAccount with this"
  value       = module.irsa.role_arn
}

output "db_secret_arn" {
  description = "Secrets Manager ARN for DB password"
  value       = module.database.db_secret_arn
  sensitive   = true
}

output "db_password" {
  description = "Generated RDS master password"
  value       = module.database.db_password
  sensitive   = true
}

output "redis_auth_token_secret_arn" {
  description = "Secrets Manager ARN for Redis AUTH token"
  value       = module.cache.redis_auth_token_secret_arn
  sensitive   = true
}

output "redis_auth_token" {
  description = "Generated Redis AUTH token"
  value       = module.cache.redis_auth_token
  sensitive   = true
}

output "rds_kms_key_arn" {
  description = "KMS key ARN for RDS encryption"
  value       = aws_kms_key.rds.arn
}
