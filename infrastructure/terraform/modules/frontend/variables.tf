variable "prefix"      { type = string }
variable "tags"        { type = map(string) }
variable "api_endpoint" { type = string }
variable "domain_name" {
  type    = string
  default = ""
}
