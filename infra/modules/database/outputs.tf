output "db_endpoint" {
  description = "RDS endpoint in host:port format."
  value       = module.rds.db_instance_endpoint
}

output "db_name" {
  description = "PostgreSQL database name."
  value       = module.rds.db_instance_name
}

output "db_secret_arn" {
  description = "Secrets Manager ARN for the RDS password."
  value       = aws_secretsmanager_secret.db_password.arn
}

output "db_password" {
  description = "Generated RDS master password."
  value       = random_password.db_password.result
  sensitive   = true
}
