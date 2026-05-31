terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }
}

variable "name_prefix" { type = string }
variable "vpc_id" { type = string }
variable "eks_node_sg_id" { type = string }
variable "tags" { type = map(string) }

# ── RDS Security Group ────────────────────────────────────────────────────────

resource "aws_security_group" "rds" {
  name        = "${var.name_prefix}-rds-sg"
  description = "Allow PostgreSQL access from EKS nodes only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from EKS nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.eks_node_sg_id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] #tfsec:ignore:aws-ec2-no-public-egress-sgr
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-rds-sg" })

  lifecycle {
    create_before_destroy = true
  }
}

# ── ElastiCache Security Group ────────────────────────────────────────────────

resource "aws_security_group" "redis" {
  name        = "${var.name_prefix}-redis-sg"
  description = "Allow Redis access from EKS nodes only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis from EKS nodes"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.eks_node_sg_id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] #tfsec:ignore:aws-ec2-no-public-egress-sgr
  }

  tags = merge(var.tags, { Name = "${var.name_prefix}-redis-sg" })

  lifecycle {
    create_before_destroy = true
  }
}

output "rds_sg_id" {
  value = aws_security_group.rds.id
}

output "redis_sg_id" {
  value = aws_security_group.redis.id
}
