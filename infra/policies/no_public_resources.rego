package terraform.no_public_resources

import rego.v1

# RDS must not be publicly accessible
deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_db_instance"
  resource.change.actions[_] in {"create", "update"}
  resource.change.after.publicly_accessible == true
  msg := sprintf("RDS instance %q must not be publicly_accessible", [resource.address])
}

# Security groups must not allow unrestricted inbound on DB/cache ports
dangerous_ports := {5432, 6379, 3306, 1433, 27017}

deny contains msg if {
  resource := input.resource_changes[_]
  resource.type == "aws_security_group"
  resource.change.actions[_] in {"create", "update"}

  ingress := resource.change.after.ingress[_]
  ingress.cidr_blocks[_] == "0.0.0.0/0"
  port := numbers.range(ingress.from_port, ingress.to_port)[_]
  dangerous_ports[port]

  msg := sprintf(
    "Security group %q allows unrestricted inbound on port %d (0.0.0.0/0)",
    [resource.address, port]
  )
}
