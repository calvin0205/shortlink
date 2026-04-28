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

# Primary region — Lambda, DynamoDB, API Gateway
provider "aws" {
  region = var.aws_region
}

# ACM certificates for CloudFront MUST be in us-east-1
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

locals {
  prefix = "${var.project}-${var.environment}"
  tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# ── Modules ───────────────────────────────────────────────────────────────────

module "storage" {
  source  = "./modules/storage"
  prefix  = local.prefix
  tags    = local.tags
}

module "api" {
  source        = "./modules/api"
  prefix        = local.prefix
  tags          = local.tags
  table_name    = module.storage.table_name
  table_arn     = module.storage.table_arn
  aws_region    = var.aws_region
  base_url      = "https://${var.domain_name}"
}

module "frontend" {
  source              = "./modules/frontend"
  prefix              = local.prefix
  tags                = local.tags
  api_endpoint        = module.api.invoke_url
  domain_name         = var.domain_name
  acm_certificate_arn = module.dns.certificate_arn

  depends_on = [module.dns]
}

module "dns" {
  source              = "./modules/dns"
  domain_name         = var.domain_name
  cloudfront_domain   = module.frontend.cloudfront_domain
  cloudfront_zone_id  = module.frontend.cloudfront_zone_id

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }
}
