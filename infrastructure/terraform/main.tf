terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }

  # Uncomment after creating the bucket manually once:
  # backend "s3" {
  #   bucket = "YOUR-TERRAFORM-STATE-BUCKET"
  #   key    = "otsentinel/terraform.tfstate"
  #   region = "ap-northeast-1"
  # }
}

provider "aws" {
  region = var.aws_region
}

# Only needed when deploying with a custom domain (ACM certs must be in us-east-1 for CloudFront)
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

locals {
  prefix     = "${var.project}-${var.environment}"
  has_domain = var.domain_name != ""
  # base_url priority: explicit override > custom domain > placeholder (updated after first deploy)
  base_url = (
    var.base_url_override != "" ? var.base_url_override :
    local.has_domain         ? "https://${var.domain_name}" :
    "https://pending-cloudfront-url"
  )
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ── Modules ───────────────────────────────────────────────────────────────────

module "storage" {
  source = "./modules/storage"
  prefix = local.prefix
  tags   = local.tags
}

module "api" {
  source     = "./modules/api"
  prefix     = local.prefix
  tags       = local.tags
  aws_region = var.aws_region
  base_url   = local.base_url
  jwt_secret = var.jwt_secret

  users_table_name     = module.storage.users_table_name
  users_table_arn      = module.storage.users_table_arn
  devices_table_name   = module.storage.devices_table_name
  devices_table_arn    = module.storage.devices_table_arn
  incidents_table_name = module.storage.incidents_table_name
  incidents_table_arn  = module.storage.incidents_table_arn
  audit_table_name     = module.storage.audit_table_name
  audit_table_arn      = module.storage.audit_table_arn
  metrics_table_name   = module.storage.metrics_table_name
  metrics_table_arn    = module.storage.metrics_table_arn
}

module "frontend" {
  source       = "./modules/frontend"
  prefix       = local.prefix
  tags         = local.tags
  api_endpoint = module.api.invoke_url
  domain_name  = var.domain_name
}

# ── DNS + ACM (only when domain_name is provided) ─────────────────────────────

module "dns" {
  count  = local.has_domain ? 1 : 0
  source = "./modules/dns"

  domain_name        = var.domain_name
  cloudfront_domain  = module.frontend.cloudfront_domain
  cloudfront_zone_id = module.frontend.cloudfront_zone_id

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }
}
