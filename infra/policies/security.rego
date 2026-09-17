package main

required_tags := {"project", "environment", "owner", "cost_center", "managed_by"}

taggable_resource_types := {
  "aws_vpc",
  "aws_subnet",
  "aws_security_group",
  "aws_db_subnet_group",
  "aws_db_instance",
  "aws_elasticache_subnet_group",
  "aws_elasticache_replication_group",
  "aws_iam_role",
  "aws_iam_openid_connect_provider",
  "aws_eks_cluster",
  "aws_eks_node_group",
}

deny[msg] {
  change := input.resource_changes[_]
  change.type == "aws_db_instance"
  change.change.after.publicly_accessible != false
  msg := sprintf("%s must not be publicly accessible", [change.address])
}

deny[msg] {
  change := input.resource_changes[_]
  change.type == "aws_db_instance"
  change.change.after.storage_encrypted != true
  msg := sprintf("%s must enable storage encryption", [change.address])
}

deny[msg] {
  change := input.resource_changes[_]
  change.type == "aws_elasticache_replication_group"
  not change.change.after.subnet_group_name
  msg := sprintf("%s must use a private ElastiCache subnet group", [change.address])
}

deny[msg] {
  change := input.resource_changes[_]
  taggable_resource_types[change.type]
  tag := required_tags[_]
  not change.change.after.tags[tag]
  msg := sprintf("%s is missing required tag %s", [change.address, tag])
}
