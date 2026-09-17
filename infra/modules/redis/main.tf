variable "name_prefix" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "allowed_security_groups" { type = map(string) }
variable "node_type" { type = string }
variable "engine_version" { type = string }
variable "tags" { type = map(string) }

resource "aws_elasticache_subnet_group" "this" {
  name       = "${var.name_prefix}-redis"
  subnet_ids = var.private_subnet_ids
  tags       = merge(var.tags, { Name = "${var.name_prefix}-redis" })
}

resource "aws_security_group" "this" {
  name        = "${var.name_prefix}-redis"
  description = "Redis ingress from approved EKS workload security groups only"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "${var.name_prefix}-redis" })
}

resource "aws_vpc_security_group_ingress_rule" "redis_from_eks" {
  for_each = var.allowed_security_groups

  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = each.value
  ip_protocol                  = "tcp"
  from_port                    = 6379
  to_port                      = 6379
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.this.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id       = "${var.name_prefix}-redis"
  description                = "InsightHub Redis 7 queue"
  engine                     = "redis"
  engine_version             = var.engine_version
  node_type                  = var.node_type
  num_cache_clusters         = 1
  automatic_failover_enabled = false
  subnet_group_name          = aws_elasticache_subnet_group.this.name
  security_group_ids         = [aws_security_group.this.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  tags                       = merge(var.tags, { Name = "${var.name_prefix}-redis" })
}

output "primary_endpoint" { value = aws_elasticache_replication_group.this.primary_endpoint_address }
