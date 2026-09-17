variable "name_prefix" { type = string }
variable "vpc_cidr" { type = string }
variable "private_subnets" {
  type = map(object({
    availability_zone = string
    cidr_block        = string
  }))
}
variable "tags" { type = map(string) }

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = merge(var.tags, { Name = "${var.name_prefix}-vpc" })
}

resource "aws_subnet" "private" {
  for_each = var.private_subnets

  vpc_id                  = aws_vpc.this.id
  availability_zone       = each.value.availability_zone
  cidr_block              = each.value.cidr_block
  map_public_ip_on_launch = false
  tags = merge(var.tags, {
    Name                              = "${var.name_prefix}-private-${each.key}"
    "kubernetes.io/role/internal-elb" = "1"
  })
}

output "vpc_id" { value = aws_vpc.this.id }
output "private_subnet_ids" { value = [for subnet in aws_subnet.private : subnet.id] }
