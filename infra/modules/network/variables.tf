variable "name" {
  description = "Resource name prefix."
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR."
  type        = string
}

variable "availability_zone_ids" {
  description = "Two stable AWS availability-zone IDs used by every subnet tier."
  type        = list(string)

  validation {
    condition     = length(var.availability_zone_ids) == 2 && var.availability_zone_ids[0] != var.availability_zone_ids[1]
    error_message = "availability_zone_ids must contain exactly two distinct zone IDs."
  }
}

variable "tags" {
  description = "Common resource tags."
  type        = map(string)
}
