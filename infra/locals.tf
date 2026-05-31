locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    project     = var.project_name
    environment = var.environment
    owner       = var.owner
    cost_center = var.cost_center
    managed_by  = "terraform"
  }

  # Derived CIDR slices (10.0.0.0/16 split into /24 subnets)
  public_subnets  = [for i, az in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, i)]
  private_subnets = [for i, az in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, i + 10)]
  db_subnets      = [for i, az in var.availability_zones : cidrsubnet(var.vpc_cidr, 8, i + 20)]
}
