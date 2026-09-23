variable "aws_region" {
  description = "AWS region containing the ALB origin."
  type        = string
  default     = "ap-southeast-1"
}

variable "origin_domain_name" {
  description = "Public ALB DNS name created by the InsightHub Ingress."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9.-]+\\.elb\\.amazonaws\\.com$", var.origin_domain_name))
    error_message = "origin_domain_name must be an AWS ELB hostname."
  }
}

variable "tags" {
  description = "Standard Day 03 ownership and cleanup tags."
  type        = map(string)
}
