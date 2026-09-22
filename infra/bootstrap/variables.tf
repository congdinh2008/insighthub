variable "aws_region" {
  description = "Region containing the state bucket and deployment resources."
  type        = string
  default     = "ap-southeast-1"
}

variable "state_bucket_name" {
  description = "Globally unique S3 bucket name for sensitive state and lock files."
  type        = string
}

variable "github_repository" {
  description = "Exact owner/repository allowed to request deployment credentials."
  type        = string
  default     = "congdinh2008/insighthub"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must use owner/repository format."
  }
}

variable "github_environment" {
  description = "Protected GitHub Environment encoded in the OIDC subject."
  type        = string
  default     = "insighthub-dev"
}

variable "github_plan_environment" {
  description = "GitHub Environment used only by the read-only Terraform plan role."
  type        = string
  default     = "insighthub-dev-plan"
}

variable "plan_policy_arn" {
  description = "Pre-reviewed read-only discovery policy for Terraform plan."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:policy/", var.plan_policy_arn))
    error_message = "plan_policy_arn must be a customer-managed IAM policy ARN."
  }
}

variable "deployment_policy_arn" {
  description = "Pre-reviewed least-privilege policy for this sandbox lab. AdministratorAccess is rejected."
  type        = string

  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:policy/", var.deployment_policy_arn)) && !endswith(var.deployment_policy_arn, "/AdministratorAccess")
    error_message = "deployment_policy_arn must be a customer-managed policy ARN and cannot be AdministratorAccess."
  }
}

variable "owner" {
  description = "Lab resource owner."
  type        = string
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
  description = "RFC3339 cleanup deadline."
  type        = string
}
