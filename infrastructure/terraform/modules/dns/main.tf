###############################################################################
# DNS + TLS
#
# Flow:
#   1. Look up the pre-existing Route53 hosted zone for your domain
#   2. Request an ACM TLS certificate (DNS validation)
#   3. Create the DNS CNAME that proves ownership → certificate becomes ISSUED
#   4. Create the A/AAAA alias records pointing to CloudFront
###############################################################################

data "aws_route53_zone" "main" {
  name         = var.domain_name
  private_zone = false
}

# ACM must be in us-east-1 for CloudFront — use the aliased provider
resource "aws_acm_certificate" "main" {
  provider          = aws.us_east_1
  domain_name       = var.domain_name
  validation_method = "DNS"

  # Allow replace-in-place on domain changes instead of destroying live cert
  lifecycle {
    create_before_destroy = true
  }
}

# DNS records that prove to ACM we own the domain
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  }

  zone_id = data.aws_route53_zone.main.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

# Wait until ACM has validated and issued the certificate
resource "aws_acm_certificate_validation" "main" {
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}

# A record (IPv4) — alias to CloudFront (no TTL needed for alias records)
resource "aws_route53_record" "apex_a" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = var.cloudfront_domain
    zone_id                = var.cloudfront_zone_id
    evaluate_target_health = false
  }
}

# AAAA record (IPv6) — same alias target
resource "aws_route53_record" "apex_aaaa" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "AAAA"

  alias {
    name                   = var.cloudfront_domain
    zone_id                = var.cloudfront_zone_id
    evaluate_target_health = false
  }
}
