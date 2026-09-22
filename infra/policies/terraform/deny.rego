package main

import rego.v1

required_tags := {"project", "environment", "owner", "cost_center", "managed_by"}
tagged_types := {
  "aws_vpc", "aws_subnet", "aws_eks_cluster", "aws_eks_node_group",
  "aws_db_instance", "aws_elasticache_replication_group", "aws_ecr_repository",
  "aws_iam_role", "aws_kms_key", "aws_secretsmanager_secret",
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.change.actions != ["delete"]
  tagged_types[resource.type]
  tags := object.get(resource.change.after, "tags", {})
  missing := required_tags - object.keys(tags)
  count(missing) > 0
  msg := sprintf("%s is missing required tags: %v", [resource.address, sort(missing)])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_db_instance"
  object.get(resource.change.after, "publicly_accessible", true)
  msg := sprintf("%s exposes RDS publicly", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_db_instance"
  not object.get(resource.change.after, "storage_encrypted", false)
  msg := sprintf("%s must encrypt RDS storage", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_elasticache_replication_group"
  not object.get(resource.change.after, "at_rest_encryption_enabled", false)
  msg := sprintf("%s must encrypt Redis at rest", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_elasticache_replication_group"
  not object.get(resource.change.after, "transit_encryption_enabled", false)
  msg := sprintf("%s must enable Redis TLS", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_security_group"
  ingress := object.get(resource.change.after, "ingress", [])[_]
  cidr := object.get(ingress, "cidr_blocks", [])[_]
  cidr == "0.0.0.0/0"
  msg := sprintf("%s has world-open ingress", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_eks_cluster"
  config := object.get(resource.change.after, "vpc_config", [])[0]
  cidr := object.get(config, "public_access_cidrs", [])[_]
  cidr == "0.0.0.0/0"
  msg := sprintf("%s has world-open Kubernetes API", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_db_instance"
  not startswith(object.get(resource.change.after, "instance_class", ""), "db.t4g.")
  msg := sprintf("%s uses an unapproved RDS class", [resource.address])
}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_elasticache_replication_group"
  not startswith(object.get(resource.change.after, "node_type", ""), "cache.t4g.")
  msg := sprintf("%s uses an unapproved Redis node type", [resource.address])
}
