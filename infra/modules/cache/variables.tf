variable "name_prefix" {
  description = "Name prefix for cache resources."
  type        = string
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type."
  type        = string
}

variable "redis_num_cache_nodes" {
  description = "Number of Redis cache nodes."
  type        = number
}

variable "subnet_ids" {
  description = "Private subnet IDs for the Redis subnet group."
  type        = list(string)
}

variable "security_group_ids" {
  description = "Security groups attached to Redis."
  type        = list(string)
}

variable "elasticache_kms_key_arn" {
  description = "KMS key ARN for ElastiCache encryption."
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
