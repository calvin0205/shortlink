output "certificate_arn" { value = aws_acm_certificate_validation.main.certificate_arn }
output "nameservers"     { value = data.aws_route53_zone.main.name_servers }
