terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

resource "random_password" "auth_token" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "auth_token" {
  name                    = "${var.name_prefix}/redis/auth-token"
  description             = "ElastiCache Redis AUTH token for InsightHub"
  recovery_window_in_days = 7
  kms_key_id              = var.secrets_kms_key_arn

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "auth_token" {
  secret_id     = aws_secretsmanager_secret.auth_token.id
  secret_string = random_password.auth_token.result
}

resource "aws_elasticache_parameter_group" "redis" {
  name        = "${var.name_prefix}-redis7"
  family      = "redis7"
  description = "InsightHub Redis 7 parameter group"

  tags = var.tags
}

resource "aws_elasticache_subnet_group" "redis" {
  name        = "${var.name_prefix}-redis-subnet"
  description = "Subnet group for InsightHub Redis"
  subnet_ids  = var.subnet_ids

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "slow_logs" {
  name              = "/insighthub/${var.environment}/redis/slow-logs"
  retention_in_days = 365
  kms_key_id        = var.elasticache_kms_key_arn

  tags = var.tags
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${var.name_prefix}-redis"
  description          = "InsightHub ARQ job queue - Redis 7"

  node_type            = var.redis_node_type
  num_cache_clusters   = var.redis_num_cache_nodes
  engine_version       = "7.1"
  port                 = 6379
  parameter_group_name = aws_elasticache_parameter_group.redis.name

  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = var.security_group_ids

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = random_password.auth_token.result
  kms_key_id                 = var.elasticache_kms_key_arn

  snapshot_retention_limit = 7
  snapshot_window          = "05:00-06:00"

  automatic_failover_enabled = var.redis_num_cache_nodes > 1
  multi_az_enabled           = var.redis_num_cache_nodes > 1

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.slow_logs.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  tags = var.tags
}
