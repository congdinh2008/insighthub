locals {
  name = "insighthub-${var.environment}"
  common_tags = {
    project     = "insighthub"
    environment = var.environment
    owner       = var.owner
    cost_center = var.cost_center
    managed_by  = "terraform"
    Class       = "DO2603"
    LabId       = var.lab_id
    ExpiresAt   = var.expires_at
  }
}
