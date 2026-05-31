variable "name_prefix" {
  description = "Name prefix for database resources."
  type        = string
}

variable "db_name" {
  description = "PostgreSQL database name."
  type        = string
}

variable "db_username" {
  description = "PostgreSQL master username."
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class."
  type        = string
}

variable "db_allocated_storage" {
  description = "Initial RDS allocated storage in GB."
  type        = number
}

variable "db_multi_az" {
  description = "Enable RDS Multi-AZ."
  type        = bool
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "db_subnet_group_name" {
  description = "Database subnet group name."
  type        = string
}

variable "vpc_security_group_ids" {
  description = "Security groups attached to the RDS instance."
  type        = list(string)
}

variable "rds_kms_key_arn" {
  description = "KMS key ARN for RDS storage encryption."
  type        = string
}

variable "secrets_kms_key_arn" {
  description = "KMS key ARN for Secrets Manager encryption."
  type        = string
}

variable "tags" {
  description = "Common tags applied to resources."
  type        = map(string)
}
