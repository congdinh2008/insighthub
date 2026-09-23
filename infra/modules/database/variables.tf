variable "name" {
  description = "Database resource name prefix."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID."
  type        = string
}

variable "subnet_ids" {
  description = "Private data subnets."
  type        = list(string)
}

variable "application_sg_id" {
  description = "Only security group allowed to connect to PostgreSQL."
  type        = string
}

variable "instance_class" {
  description = "RDS instance class."
  type        = string
}

variable "backup_retention_days" {
  description = "Automated backup retention."
  type        = number
}

variable "environment" {
  description = "Environment controlling deletion safeguards."
  type        = string
}

variable "tags" {
  description = "Common resource tags."
  type        = map(string)
}
