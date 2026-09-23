variable "name" {
  description = "EKS cluster name."
  type        = string
}

variable "kubernetes_version" {
  description = "EKS control plane version."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnets used by EKS nodes and control plane ENIs."
  type        = list(string)
}

variable "admin_cidrs" {
  description = "Known CIDRs allowed to reach the public EKS API endpoint."
  type        = list(string)
}

variable "cluster_admin_principal_arn" {
  description = "Reviewed role allowed to administer this cluster."
  type        = string
}

variable "node_instance_types" {
  description = "EKS managed node instance types."
  type        = list(string)
}

variable "node_desired_size" {
  description = "Desired node count."
  type        = number
}

variable "tags" {
  description = "Common resource tags."
  type        = map(string)
}
