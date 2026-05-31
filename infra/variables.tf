variable "aws_region" {
  description = "AWS region to deploy InsightHub"
  type        = string
  default     = "ap-southeast-1"
}

variable "environment" {
  description = "Deployment environment: dev | staging | prod"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name, used as prefix for all resources"
  type        = string
  default     = "insighthub"
}

variable "owner" {
  description = "Team or individual owning these resources"
  type        = string
  default     = "platform-team"
}

variable "cost_center" {
  description = "FinOps cost center code"
  type        = string
  default     = "CC-001"
}

# ── VPC ──────────────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "AZs to use (must be ≥2 for RDS Multi-AZ)"
  type        = list(string)
  default     = ["ap-southeast-1a", "ap-southeast-1b", "ap-southeast-1c"]
}

# ── EKS ──────────────────────────────────────────────────────────────────────

variable "eks_cluster_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.31"
}

variable "eks_node_instance_type" {
  description = "EC2 instance type for EKS managed node group"
  type        = string
  default     = "t3.medium"
}

variable "eks_node_min_size" {
  description = "Minimum number of EKS worker nodes"
  type        = number
  default     = 1
}

variable "eks_node_max_size" {
  description = "Maximum number of EKS worker nodes"
  type        = number
  default     = 3
}

variable "eks_node_desired_size" {
  description = "Desired number of EKS worker nodes"
  type        = number
  default     = 2
}

# ── RDS ──────────────────────────────────────────────────────────────────────

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "insighthub"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "insighthub"
  sensitive   = true
}

variable "db_multi_az" {
  description = "Enable RDS Multi-AZ (false for dev, true for prod)"
  type        = bool
  default     = false
}

# ── ElastiCache ───────────────────────────────────────────────────────────────

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of Redis cache nodes (1 = single node, ≥2 = cluster)"
  type        = number
  default     = 1
}
