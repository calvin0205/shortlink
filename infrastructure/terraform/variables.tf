variable "aws_region" {
  description = "Primary AWS region for Lambda, DynamoDB, and API Gateway"
  type        = string
  default     = "ap-northeast-1"
}

variable "domain_name" {
  description = "Custom domain (e.g. otsentinel.example.com). Leave empty to use the auto-generated CloudFront URL."
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
  default     = "otsentinel"
}

variable "base_url_override" {
  description = "Override the base URL (e.g. https://xxxxx.cloudfront.net). Leave empty on first deploy."
  type        = string
  default     = ""
}

variable "jwt_secret" {
  description = "JWT signing secret for authentication"
  type        = string
  default     = "dev-secret-change-in-prod"
  sensitive   = true
}

variable "alert_email" {
  description = "Email address for L1/L2 escalation alerts via SNS. Leave empty to disable."
  type        = string
  default     = ""
}
