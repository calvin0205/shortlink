variable "aws_region" {
  description = "Primary AWS region for Lambda, DynamoDB, and API Gateway"
  type        = string
  default     = "ap-northeast-1"
}

variable "domain_name" {
  description = "Your root domain (e.g. shortlink.example.com). Must already have a hosted zone in Route53."
  type        = string
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
