resource "aws_dynamodb_table" "links" {
  name         = "${var.prefix}-links"
  billing_mode = "PAY_PER_REQUEST"  # no capacity planning needed; auto-scales
  hash_key     = "code"

  attribute {
    name = "code"
    type = "S"
  }

  # Automatically purge items after TTL field "expires_at" (if set)
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = var.tags
}
