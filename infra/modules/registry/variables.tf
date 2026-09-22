variable "name" {
  description = "Registry repository prefix."
  type        = string
}

variable "tags" {
  description = "Common resource tags."
  type        = map(string)
}
