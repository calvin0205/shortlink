variable "prefix"     { type = string }
variable "tags"       { type = map(string) }
variable "aws_region" { type = string }
variable "base_url"   { type = string }

variable "users_table_name"     { type = string }
variable "users_table_arn"      { type = string }
variable "devices_table_name"   { type = string }
variable "devices_table_arn"    { type = string }
variable "incidents_table_name" { type = string }
variable "incidents_table_arn"  { type = string }
variable "audit_table_name"     { type = string }
variable "audit_table_arn"      { type = string }

variable "jwt_secret" {
  description = "JWT signing secret for authentication"
  type        = string
  default     = "dev-secret-change-in-prod"
  sensitive   = true
}
