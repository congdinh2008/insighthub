output "cluster_name" {
  description = "EKS cluster name."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS API endpoint."
  value       = module.eks.cluster_endpoint
}

output "namespace" {
  description = "InsightHub Kubernetes namespace."
  value       = kubernetes_namespace_v1.insighthub_dev.metadata[0].name
}

output "service_account_name" {
  description = "IRSA-enabled Kubernetes ServiceAccount name."
  value       = kubernetes_service_account_v1.insighthub.metadata[0].name
}

output "irsa_role_arn" {
  description = "IAM role ARN bound to the InsightHub ServiceAccount."
  value       = module.irsa.role_arn
}

output "rds_endpoint" {
  description = "Non-secret RDS endpoint address."
  value       = module.rds.endpoint
}

output "rds_master_user_secret_arn" {
  description = "RDS-managed Secrets Manager secret ARN; its value is not output."
  value       = module.rds.master_user_secret_arn
}

output "redis_primary_endpoint" {
  description = "Non-secret ElastiCache primary endpoint address."
  value       = module.redis.primary_endpoint
}
