# ── S3 bucket (private — only CloudFront can read it) ─────────────────────────

resource "aws_s3_bucket" "frontend" {
  bucket        = "${var.prefix}-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
  tags          = var.tags
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket                  = aws_s3_bucket.frontend.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Origin Access Control — modern replacement for Origin Access Identity
resource "aws_cloudfront_origin_access_control" "s3" {
  name                              = "${var.prefix}-s3-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

data "aws_iam_policy_document" "s3_cloudfront" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.main.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.s3_cloudfront.json
}

# ── CloudFront distribution ────────────────────────────────────────────────────

resource "aws_cloudfront_distribution" "main" {
  enabled         = true
  is_ipv6_enabled = true
  price_class     = "PriceClass_100"  # US, EU, Asia only (cheapest)
  tags                = var.tags

  # Origin 1 — S3 static frontend
  origin {
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id                = "s3-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.s3.id
  }

  # Origin 2 — API Gateway (Lambda backend)
  origin {
    domain_name = replace(var.api_endpoint, "/^https?://([^/]+).*/", "$1")
    origin_id   = "api-gateway"
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # /static/* → S3 (CSS, JS — cached aggressively)
  ordered_cache_behavior {
    path_pattern           = "/static/*"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "s3-frontend"
    viewer_protocol_policy = "redirect-to-https"
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6"  # CachingOptimized (built-in)
    compress               = true
  }

  # /api/* → Lambda (API calls, no cache)
  ordered_cache_behavior {
    path_pattern             = "/api/*"
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD"]
    target_origin_id         = "api-gateway"
    viewer_protocol_policy   = "redirect-to-https"
    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"  # CachingDisabled (built-in)
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"  # AllViewerExceptHostHeader
    compress                 = true
  }

  # /* → Lambda (handles GET / and GET /{code} redirects)
  default_cache_behavior {
    allowed_methods          = ["GET", "HEAD"]
    cached_methods           = ["GET", "HEAD"]
    target_origin_id         = "api-gateway"
    viewer_protocol_policy   = "redirect-to-https"
    cache_policy_id          = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"  # CachingDisabled
    origin_request_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"  # AllViewerExceptHostHeader
    compress                 = true
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  # Use custom ACM cert when a domain is provided, otherwise use the default
  # CloudFront certificate (*.cloudfront.net — HTTPS still works, just uglier URL)
  dynamic "viewer_certificate" {
    for_each = var.domain_name != "" ? [] : [1]
    content {
      cloudfront_default_certificate = true
    }
  }

  aliases = var.domain_name != "" ? [var.domain_name] : []
}
