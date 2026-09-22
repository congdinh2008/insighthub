locals {
  namespace = "insighthub-${var.environment}"
  labels = {
    "app.kubernetes.io/name"       = "insighthub"
    "app.kubernetes.io/managed-by" = "terraform"
    "environment"                  = var.environment
  }
}

resource "kubernetes_namespace_v1" "insighthub" {
  metadata {
    name   = local.namespace
    labels = local.labels
  }
}

resource "kubernetes_service_account_v1" "insighthub" {
  metadata {
    name      = "insighthub"
    namespace = kubernetes_namespace_v1.insighthub.metadata[0].name
    labels    = local.labels
    annotations = {
      "eks.amazonaws.com/role-arn" = var.application_role_arn
    }
  }

  automount_service_account_token = true
}

resource "kubernetes_role_v1" "runtime" {
  metadata {
    name      = "insighthub-runtime"
    namespace = kubernetes_namespace_v1.insighthub.metadata[0].name
    labels    = local.labels
  }

  rule {
    api_groups = [""]
    resources  = ["configmaps"]
    verbs      = ["get", "list"]
  }
}

resource "kubernetes_role_binding_v1" "runtime" {
  metadata {
    name      = "insighthub-runtime"
    namespace = kubernetes_namespace_v1.insighthub.metadata[0].name
    labels    = local.labels
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.runtime.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account_v1.insighthub.metadata[0].name
    namespace = kubernetes_namespace_v1.insighthub.metadata[0].name
  }
}

check "secret_scope" {
  assert {
    condition     = can(regex("^arn:aws:secretsmanager:[a-z0-9-]+:[0-9]{12}:secret:insighthub/", var.application_secret_arn))
    error_message = "application_secret_arn must point to the InsightHub secret path."
  }
}
