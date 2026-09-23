output "state_bucket" {
  description = "S3 bucket supplied to backend initialization."
  value       = aws_s3_bucket.state.id
}

output "state_kms_key_arn" {
  description = "KMS key supplied to backend initialization."
  value       = aws_kms_key.state.arn
}

output "github_deploy_role_arn" {
  description = "OIDC role used by reviewed deployments."
  value       = aws_iam_role.github_deploy.arn
}

output "github_plan_role_arn" {
  description = "OIDC role used by Terraform plan jobs."
  value       = aws_iam_role.github_plan.arn
}
