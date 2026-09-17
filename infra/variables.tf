variable "aws_region" {
  description = "AWS region selected for the approved sandbox/lab."
  type        = string
}

variable "project" {
  description = "Required project tag value."
  type        = string
  nullable    = false
}

variable "environment" {
  description = "Required environment tag value. This root module deploys the dev environment."
  type        = string
  default     = "dev"

  validation {
    condition     = var.environment == "dev"
    error_message = "This root module is scoped to the dev environment."
  }
}

variable "owner" {
  description = "Required accountable-owner tag value."
  type        = string
  nullable    = false
}

variable "cost_center" {
  description = "Required cost-center tag value."
  type        = string
  nullable    = false
}

variable "cluster_name" {
  description = "Name for the EKS cluster."
  type        = string
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version approved for the target lab."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR for the dedicated InsightHub VPC."
  type        = string
}

variable "private_subnets" {
  description = "Private subnet CIDRs keyed by availability zone, used by EKS, RDS, and ElastiCache."
  type = map(object({
    availability_zone = string
    cidr_block        = string
  }))

  validation {
    condition     = length(var.private_subnets) >= 2
    error_message = "At least two private subnets in distinct availability zones are required."
  }
}

variable "eks_node_instance_types" {
  description = "Approved instance types for the managed EKS node group."
  type        = list(string)
}

variable "eks_node_desired_size" {
  description = "Desired managed node count."
  type        = number
}

variable "eks_node_min_size" {
  description = "Minimum managed node count."
  type        = number
}

variable "eks_node_max_size" {
  description = "Maximum managed node count."
  type        = number
}

variable "rds_instance_class" {
  description = "Approved RDS instance class."
  type        = string
}

variable "rds_allocated_storage" {
  description = "Allocated RDS storage in GiB."
  type        = number
}

variable "rds_engine_version" {
  description = "Approved PostgreSQL 16 engine patch version with pgvector support in the selected region."
  type        = string

  validation {
    condition     = can(regex("^16(\\.|$)", var.rds_engine_version))
    error_message = "rds_engine_version must be PostgreSQL major version 16."
  }
}

variable "rds_database_name" {
  description = "Initial non-secret database name."
  type        = string
  default     = "insighthub"
}

variable "rds_master_username" {
  description = "Initial RDS master username; its password is managed by RDS in Secrets Manager."
  type        = string
  default     = "insighthub_admin"
}

variable "redis_node_type" {
  description = "Approved ElastiCache node type."
  type        = string
}

variable "redis_engine_version" {
  description = "Approved Redis 7 engine version."
  type        = string

  validation {
    condition     = can(regex("^7(\\.|$)", var.redis_engine_version))
    error_message = "redis_engine_version must be Redis major version 7."
  }
}

variable "additional_tags" {
  description = "Optional non-sensitive tags, for example lab lifecycle tags. Required tags cannot be overridden."
  type        = map(string)
  default     = {}
}
