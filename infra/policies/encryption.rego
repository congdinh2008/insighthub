package terraform.encryption

import rego.v1

# RDS must have storage_encrypted = true
deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_db_instance"
  resource.change.actions[_] in {"create", "update"}
  not resource.change.after.storage_encrypted
  msg := sprintf("RDS instance %q must have storage_encrypted = true", [resource.address])
}

# ElastiCache must have at_rest_encryption_enabled = true
deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_elasticache_replication_group"
  resource.change.actions[_] in {"create", "update"}
  not resource.change.after.at_rest_encryption_enabled
  msg := sprintf("ElastiCache %q must have at_rest_encryption_enabled = true", [resource.address])
}

# ElastiCache must have transit_encryption_enabled = true
deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_elasticache_replication_group"
  resource.change.actions[_] in {"create", "update"}
  not resource.change.after.transit_encryption_enabled
  msg := sprintf("ElastiCache %q must have transit_encryption_enabled = true", [resource.address])
}

# KMS keys must have key rotation enabled
deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_kms_key"
  resource.change.actions[_] in {"create", "update"}
  not resource.change.after.enable_key_rotation
  msg := sprintf("KMS key %q must have enable_key_rotation = true", [resource.address])
}
