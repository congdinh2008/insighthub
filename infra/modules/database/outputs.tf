output "endpoint" {
  description = "Private PostgreSQL endpoint."
  value       = aws_db_instance.this.address
}

output "port" {
  description = "PostgreSQL port."
  value       = aws_db_instance.this.port
}

output "master_secret_arn" {
  description = "AWS-managed master credential secret."
  value       = aws_db_instance.this.master_user_secret[0].secret_arn
  sensitive   = true
}

output "kms_key_arn" {
  description = "Database KMS key reused for application secrets."
  value       = aws_kms_key.this.arn
}
