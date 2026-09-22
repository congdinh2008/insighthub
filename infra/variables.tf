variable "aws_region" {
  description = "AWS region for this short-lived lab environment."
  type        = string
  default     = "ap-southeast-1"
}

variable "environment" {
  description = "Deployment environment encoded in names, state and tags."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging"], var.environment)
    error_message = "environment must be dev or staging."
  }
}

variable "owner" {
  description = "Resource owner used for cost and cleanup accountability."
  type        = string

  validation {
    condition     = length(trimspace(var.owner)) >= 3
    error_message = "owner must identify the person responsible for this lab."
  }
}

variable "cost_center" {
  description = "Cost allocation identifier."
  type        = string
}

variable "lab_id" {
  description = "Unique lab execution identifier."
  type        = string
}

variable "expires_at" {
  description = "RFC3339 cleanup deadline recorded on every taggable resource."
  type        = string

  validation {
    condition     = can(timecmp(var.expires_at, timestamp()))
    error_message = "expires_at must be an RFC3339 timestamp."
  }
}

variable "vpc_cidr" {
  description = "CIDR for the isolated InsightHub lab VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "availability_zone_ids" {
  description = "Stable availability-zone IDs for the selected AWS region."
  type        = list(string)
  default     = ["apse1-az1", "apse1-az2"]
}

variable "admin_cidrs" {
  description = "Known operator or runner CIDRs allowed to reach the EKS public API."
  type        = list(string)

  validation {
    condition = length(var.admin_cidrs) > 0 && alltrue([
      for cidr in var.admin_cidrs : cidr != "0.0.0.0/0" && cidr != "::/0"
    ])
    error_message = "admin_cidrs must be nonempty and cannot contain a world-open CIDR."
  }
}

variable "cluster_admin_principal_arn" {
  description = "Reviewed GitHub OIDC apply role ARN granted EKS cluster administration for deployment."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:role/", var.cluster_admin_principal_arn))
    error_message = "cluster_admin_principal_arn must be an IAM role ARN."
  }
}

variable "load_balancer_controller_policy_arn" {
  description = "Customer-managed IAM policy created from the pinned official AWS Load Balancer Controller policy."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:policy/", var.load_balancer_controller_policy_arn))
    error_message = "load_balancer_controller_policy_arn must be a customer-managed IAM policy ARN."
  }
}

variable "kubernetes_version" {
  description = "EKS control plane version validated for this lab."
  type        = string
  default     = "1.34"
}

variable "node_instance_types" {
  description = "Allowed EKS worker instance types."
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  description = "Desired number of lab worker nodes."
  type        = number
  default     = 2

  validation {
    condition     = var.node_desired_size >= 1 && var.node_desired_size <= 3
    error_message = "node_desired_size must be between 1 and 3 for the lab."
  }
}

variable "rds_instance_class" {
  description = "RDS instance class constrained by policy for the lab."
  type        = string
  default     = "db.t4g.micro"
}

variable "redis_node_type" {
  description = "ElastiCache node type constrained by policy for the lab."
  type        = string
  default     = "cache.t4g.micro"
}

variable "database_backup_retention_days" {
  description = "Backup retention. Dev is short-lived; production design requires 7 days."
  type        = number
  default     = 1

  validation {
    condition     = var.database_backup_retention_days >= 1 && var.database_backup_retention_days <= 7
    error_message = "backup retention must be between 1 and 7 days."
  }
}

variable "application_secret_name" {
  description = "Secrets Manager name whose JSON keys become runtime environment variables."
  type        = string
  default     = "insighthub/dev/application"
}
