package terraform.required_tags

import rego.v1

# Required tags that every resource must have
required_tags := {"project", "environment", "owner", "cost_center", "managed_by"}

# Resources that Terraform creates (exclude data sources and local_file)
taggable_resource_types := {
  "aws_instance", "aws_db_instance", "aws_elasticache_replication_group",
  "aws_kms_key", "aws_security_group", "aws_iam_role",
  "aws_secretsmanager_secret", "aws_cloudwatch_log_group",
  "aws_elasticache_subnet_group", "aws_db_parameter_group"
}

# Collect all violations
violations contains msg if {
  resource := input.resource_changes[_]
  resource.change.actions[_] in {"create", "update"}
  taggable_resource_types[resource.type]

  missing := required_tags - {tag | resource.change.after.tags[tag]}
  count(missing) > 0
  msg := sprintf("Resource %q (%s) is missing required tags: %v", [resource.address, resource.type, missing])
}

deny contains msg if {
  msg := violations[_]
}
