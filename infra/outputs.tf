output "cluster_name" {
  description = "EKS cluster used by the platform state."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS API endpoint."
  value       = module.eks.cluster_endpoint
}

output "cluster_ca_data" {
  description = "Base64 cluster CA used by the Kubernetes provider."
  value       = module.eks.cluster_ca_data
  sensitive   = true
}

output "application_role_arn" {
  description = "IRSA role read by the platform root."
  value       = aws_iam_role.application.arn
}

output "application_secret_arn" {
  description = "Secret reference populated outside Terraform."
  value       = aws_secretsmanager_secret.application.arn
}

output "load_balancer_controller_role_arn" {
  description = "IRSA role for the AWS Load Balancer Controller."
  value       = aws_iam_role.load_balancer_controller.arn
}

output "database_endpoint" {
  description = "Private RDS endpoint."
  value       = module.database.endpoint
}

output "database_master_secret_arn" {
  description = "AWS-managed RDS master secret for the one-shot bootstrap operation."
  value       = module.database.master_secret_arn
  sensitive   = true
}

output "redis_endpoint" {
  description = "Private TLS ElastiCache endpoint."
  value       = module.cache.primary_endpoint
}

output "ecr_repository_urls" {
  description = "Immutable image repositories keyed by workload."
  value       = module.registry.repository_urls
}
