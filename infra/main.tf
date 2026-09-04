resource "kubernetes_namespace_v1" "insighthub" {
  metadata {
    name = var.namespace

    labels = {
      "app.kubernetes.io/part-of"    = "insighthub"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}