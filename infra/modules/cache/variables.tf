variable "name" {
  description = "Cache resource name prefix."
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
  description = "Only security group allowed to connect to Redis."
  type        = string
}

variable "node_type" {
  description = "ElastiCache node type."
  type        = string
}

variable "environment" {
  description = "Environment controls the minimum dev topology and staging failover."
  type        = string

  validation {
    condition     = contains(["dev", "staging"], var.environment)
    error_message = "environment must be dev or staging."
  }
}

variable "tags" {
  description = "Common resource tags."
  type        = map(string)
}
