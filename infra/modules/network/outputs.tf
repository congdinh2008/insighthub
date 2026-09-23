output "vpc_id" {
  description = "Lab VPC ID."
  value       = aws_vpc.this.id
}

output "private_subnet_ids" {
  description = "Private application subnets."
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "Public load balancer subnets."
  value       = aws_subnet.public[*].id
}

output "data_subnet_ids" {
  description = "Isolated data subnets without an internet route."
  value       = aws_subnet.data[*].id
}
