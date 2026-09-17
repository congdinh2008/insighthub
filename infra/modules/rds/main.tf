variable "name_prefix" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "allowed_security_groups" { type = map(string) }
variable "instance_class" { type = string }
variable "allocated_storage" { type = number }
variable "engine_version" { type = string }
variable "database_name" { type = string }
variable "master_username" { type = string }
variable "tags" { type = map(string) }

resource "aws_db_subnet_group" "this" {
  name       = "${var.name_prefix}-db"
  subnet_ids = var.private_subnet_ids
  tags       = merge(var.tags, { Name = "${var.name_prefix}-db" })
}

resource "aws_security_group" "this" {
  name        = "${var.name_prefix}-rds"
  description = "PostgreSQL ingress from approved EKS workload security groups only"
  vpc_id      = var.vpc_id
  tags        = merge(var.tags, { Name = "${var.name_prefix}-rds" })
}

resource "aws_vpc_security_group_ingress_rule" "postgres_from_eks" {
  for_each = var.allowed_security_groups

  security_group_id            = aws_security_group.this.id
  referenced_security_group_id = each.value
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.this.id
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_db_instance" "this" {
  identifier                  = "${var.name_prefix}-postgres"
  engine                      = "postgres"
  engine_version              = var.engine_version
  instance_class              = var.instance_class
  allocated_storage           = var.allocated_storage
  storage_encrypted           = true
  publicly_accessible         = false
  db_subnet_group_name        = aws_db_subnet_group.this.name
  vpc_security_group_ids      = [aws_security_group.this.id]
  db_name                     = var.database_name
  username                    = var.master_username
  manage_master_user_password = true
  skip_final_snapshot         = true
  deletion_protection         = false
  backup_retention_period     = 0
  tags                        = merge(var.tags, { Name = "${var.name_prefix}-postgres" })
}

# pgvector is enabled after provisioning by an approved database migration using
# CREATE EXTENSION IF NOT EXISTS vector; no database password is held in Terraform.
output "endpoint" { value = aws_db_instance.this.address }
output "master_user_secret_arn" { value = aws_db_instance.this.master_user_secret[0].secret_arn }
