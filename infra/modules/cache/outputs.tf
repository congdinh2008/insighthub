output "redis_endpoint" {
  description = "ElastiCache Redis primary endpoint address."
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "redis_auth_token_secret_arn" {
  description = "Secrets Manager ARN for the Redis AUTH token."
  value       = aws_secretsmanager_secret.auth_token.arn
}

output "redis_auth_token" {
  description = "Generated Redis AUTH token."
  value       = random_password.auth_token.result
  sensitive   = true
}
