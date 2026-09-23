variable "aws_region" {
  description = "AWS region containing the EKS cluster."
  type        = string
  default     = "ap-southeast-1"
}

variable "environment" {
  description = "Environment used in the Kubernetes namespace."
  type        = string

  validation {
    condition     = contains(["dev", "staging"], var.environment)
    error_message = "environment must be dev or staging."
  }
}

variable "cluster_name" {
  description = "Existing EKS cluster from the AWS infrastructure state."
  type        = string
}

variable "application_role_arn" {
  description = "IRSA role from the AWS infrastructure state."
  type        = string
}

variable "application_secret_arn" {
  description = "Application secret read by the Secrets Store CSI provider."
  type        = string
}
