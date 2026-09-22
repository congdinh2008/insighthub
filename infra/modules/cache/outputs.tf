output "primary_endpoint" {
  description = "Primary Redis TLS endpoint."
  value       = aws_elasticache_replication_group.this.primary_endpoint_address
}
