output "cluster_name" {
  description = "EKS cluster name."
  value       = aws_eks_cluster.this.name
}

output "cluster_endpoint" {
  description = "EKS API endpoint."
  value       = aws_eks_cluster.this.endpoint
}

output "cluster_ca_data" {
  description = "Base64 EKS cluster CA."
  value       = aws_eks_cluster.this.certificate_authority[0].data
  sensitive   = true
}

output "node_security_group_id" {
  description = "EKS cluster security group used to scope data service ingress."
  value       = aws_eks_cluster.this.vpc_config[0].cluster_security_group_id
}

output "oidc_provider_arn" {
  description = "OIDC provider ARN for IRSA."
  value       = aws_iam_openid_connect_provider.this.arn
}

output "oidc_issuer_hostpath" {
  description = "OIDC issuer without scheme for IAM trust conditions."
  value       = replace(aws_iam_openid_connect_provider.this.url, "https://", "")
}
