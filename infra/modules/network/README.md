# Network module

Creates one lab VPC across two availability zones. Public subnets are reserved for the ALB, private subnets run EKS nodes through one cost-conscious NAT gateway, and data subnets have no internet route. The module enables encrypted VPC flow logs and denies all traffic through the default security group.

The single NAT gateway is a lab cost/availability tradeoff. A production design should use one NAT per active AZ or private endpoints after a workload and cost review.
