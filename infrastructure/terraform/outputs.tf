output "site_url" {
  description = "Live URL of the deployed site"
  value       = "https://${var.domain_name}"
}

output "api_invoke_url" {
  description = "API Gateway invoke URL (internal)"
  value       = module.api.invoke_url
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (needed for cache invalidation)"
  value       = module.frontend.cloudfront_distribution_id
}

output "s3_frontend_bucket" {
  description = "S3 bucket name for frontend assets"
  value       = module.frontend.bucket_name
}
