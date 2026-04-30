# Users table
resource "aws_dynamodb_table" "users" {
  name         = "${var.prefix}-users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  tags = merge(var.tags, {
    Description = "OT Sentinel users table with email GSI"
  })

  attribute { name = "PK";    type = "S" }
  attribute { name = "email"; type = "S" }

  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }
}

# Devices table
resource "aws_dynamodb_table" "devices" {
  name         = "${var.prefix}-devices"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  tags = merge(var.tags, {
    Description = "OT Sentinel devices table with status-index and site-index GSIs"
  })

  attribute { name = "PK";       type = "S" }
  attribute { name = "status";   type = "S" }
  attribute { name = "last_seen"; type = "S" }
  attribute { name = "site_id";  type = "S" }

  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    range_key       = "last_seen"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "site-index"
    hash_key        = "site_id"
    range_key       = "PK"
    projection_type = "ALL"
  }
}

# Incidents table
resource "aws_dynamodb_table" "incidents" {
  name         = "${var.prefix}-incidents"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  tags = merge(var.tags, {
    Description = "OT Sentinel incidents table with device-index and severity-index GSIs"
  })

  attribute { name = "PK";         type = "S" }
  attribute { name = "device_id";  type = "S" }
  attribute { name = "created_at"; type = "S" }
  attribute { name = "severity";   type = "S" }

  global_secondary_index {
    name            = "device-index"
    hash_key        = "device_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "severity-index"
    hash_key        = "severity"
    range_key       = "created_at"
    projection_type = "ALL"
  }
}

# Audit table
resource "aws_dynamodb_table" "audit" {
  name         = "${var.prefix}-audit"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  tags = merge(var.tags, {
    Description = "OT Sentinel audit log table with user-index GSI"
  })

  attribute { name = "PK";        type = "S" }
  attribute { name = "user_id";   type = "S" }
  attribute { name = "timestamp"; type = "S" }

  global_secondary_index {
    name            = "user-index"
    hash_key        = "user_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }
}
