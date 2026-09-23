resource "aws_kms_key" "this" {
  # checkov:skip=CKV2_AWS_64:AWS installs its account-scoped default key policy; key use is restricted by IAM and service grants.
  description             = "Encrypt ${var.name} Redis data"
  deletion_window_in_days = 7
  enable_key_rotation     = true
  tags                    = var.tags
}

resource "aws_elasticache_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.subnet_ids
  tags       = var.tags
}

resource "aws_security_group" "this" {
  name        = "${var.name}-redis"
  description = "Redis ingress from InsightHub EKS workloads only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "TLS Redis from application"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.application_sg_id]
  }

  egress {
    description = "No outbound connections are required by Redis"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["127.0.0.1/32"]
  }

  tags = var.tags
}

resource "aws_elasticache_parameter_group" "this" {
  name   = replace(var.name, "_", "-")
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "noeviction"
  }

  tags = var.tags
}

resource "aws_elasticache_replication_group" "this" {
  # checkov:skip=CKV_AWS_31:Auth tokens would persist in Terraform state; TLS, private subnets and SG-scoped access protect this lab queue.
  # checkov:skip=CKV2_AWS_50:Dev deliberately uses one minimum-cost node; staging enables Multi-AZ automatic failover.
  replication_group_id = var.name
  description          = "InsightHub asynchronous ingestion queue"

  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.node_type
  port                 = 6379
  parameter_group_name = aws_elasticache_parameter_group.this.name
  subnet_group_name    = aws_elasticache_subnet_group.this.name
  security_group_ids   = [aws_security_group.this.id]

  num_cache_clusters         = var.environment == "staging" ? 2 : 1
  automatic_failover_enabled = var.environment == "staging"
  multi_az_enabled           = var.environment == "staging"

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  kms_key_id                 = aws_kms_key.this.arn

  snapshot_retention_limit   = 1
  snapshot_window            = "17:00-18:00"
  maintenance_window         = "sun:19:00-sun:20:00"
  auto_minor_version_upgrade = true
  apply_immediately          = false

  tags = var.tags
}
