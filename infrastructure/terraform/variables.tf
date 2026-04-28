variable "aws_region" {
  description = "Primary AWS region for Lambda, DynamoDB, and API Gateway"
  type        = string
  default     = "ap-northeast-1"
}

variable "domain_name" {
  description = "Custom domain (e.g. shortlink.example.com). Leave empty to use the auto-generated CloudFront URL."
  type        = string
  default     = ""
}

variable "environment" {
  description = "Deployment environment label (dev / prod)"
  type        = string
  default     = "prod"
}

variable "project" {
  description = "Project name — used as a prefix on all resource names"
  type        = string
  default     = "shortlink"
}

variable "base_url_override" {
  description = "Override the base URL used in short links (e.g. https://xxxxx.cloudfront.net). Leave empty on first deploy, then set after CloudFront URL is known."
  type        = string
  default     = ""
}
