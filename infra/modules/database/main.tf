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

resource "aws_db_parameter_group" "postgres16" {
  name        = "${var.name_prefix}-postgres16"
  family      = "postgres16"
  description = "PostgreSQL 16 parameter group for InsightHub"

  # pgvector is enabled per database with CREATE EXTENSION vector; it is not a
  # shared_preload_libraries entry. Keep only libraries that PostgreSQL preloads.
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }

  tags = var.tags

  lifecycle {
    create_before_destroy = true
  }
}

resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "db_password" {
  name                    = "${var.name_prefix}/db/password"
  description             = "RDS master password for InsightHub"
  recovery_window_in_days = 7
  kms_key_id              = var.secrets_kms_key_arn

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

resource "aws_iam_role" "enhanced_monitoring" {
  name = "${var.name_prefix}-rds-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "monitoring.rds.amazonaws.com" }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "enhanced_monitoring" {
  role       = aws_iam_role.enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.10"

  identifier = "${var.name_prefix}-postgres"

  engine               = "postgres"
  engine_version       = "16.6"
  family               = "postgres16"
  major_engine_version = "16"
  instance_class       = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_allocated_storage * 5

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result
  port     = 5432

  parameter_group_name            = aws_db_parameter_group.postgres16.name
  create_db_parameter_group       = false
  parameter_group_use_name_prefix = false

  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = var.vpc_security_group_ids
  publicly_accessible    = false
  multi_az               = var.db_multi_az

  storage_encrypted = true
  kms_key_id        = var.rds_kms_key_arn

  backup_retention_period = 7
  backup_window           = "03:00-06:00"
  maintenance_window      = "Mon:00:00-Mon:03:00"

  monitoring_interval    = 60
  monitoring_role_arn    = aws_iam_role.enhanced_monitoring.arn
  create_monitoring_role = false

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  deletion_protection = var.environment == "prod"
  skip_final_snapshot = var.environment != "prod"

  tags = var.tags
}
