output "namespace" {
  description = "Terraform-owned InsightHub namespace."
  value       = kubernetes_namespace_v1.insighthub.metadata[0].name
}

output "service_account" {
  description = "IRSA-bound application service account."
  value       = kubernetes_service_account_v1.insighthub.metadata[0].name
}
