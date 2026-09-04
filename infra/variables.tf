variable "kubeconfig" {
  description = "Path to the kubeconfig for the target lab cluster."
  type        = string
  default     = null
}

variable "kube_context" {
  description = "Kubernetes context to manage; leave null to use the current context."
  type        = string
  default     = null
}

variable "namespace" {
  description = "Namespace used by InsightHub workloads."
  type        = string
  default     = "do2602-hcduy"
}