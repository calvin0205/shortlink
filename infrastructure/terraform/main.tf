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
  }

  # Uncomment after creating the bucket manually once:
  # backend "s3" {
  #   bucket = "YOUR-TERRAFORM-STATE-BUCKET"
  #   key    = "shortlink/terraform.tfstate"
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
  prefix   = "${var.project}-${var.environment}"
  has_domain = var.domain_name != ""
  base_url = local.has_domain ? "https://${var.domain_name}" : "https://${module.frontend.cloudfront_domain}"
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
  table_name = module.storage.table_name
  table_arn  = module.storage.table_arn
  aws_region = var.aws_region
  base_url   = local.base_url
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
