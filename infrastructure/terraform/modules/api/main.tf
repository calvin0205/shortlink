# ── Lambda package ────────────────────────────────────────────────────────────
# Build a clean deployment package:
#   1. pip install -r requirements.txt into build/
#   2. copy app/ code into build/
#   3. zip build/ → lambda_package.zip
#
# This avoids bundling .venv (which exceeds Lambda's 70 MB upload limit).

locals {
  build_dir   = "${path.module}/build"
  backend_dir = abspath("${path.root}/../../backend")
}

resource "null_resource" "lambda_build" {
  triggers = {
    # Rebuild whenever requirements or any app source file changes
    requirements = filemd5("${local.backend_dir}/requirements.txt")
    app_code     = sha256(join(",", [
      for f in sort(fileset("${local.backend_dir}/app", "**/*.py")) :
      filemd5("${local.backend_dir}/app/${f}")
    ]))
  }

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-Command"]
    command     = <<-EOT
      $build   = "${local.build_dir}"
      $backend = "${local.backend_dir}"
      if (Test-Path $build) { Remove-Item -Recurse -Force $build }
      New-Item -ItemType Directory -Force -Path $build | Out-Null
      # Download Linux-compatible wheels (Lambda runs on Amazon Linux 2 x86_64).
      # --platform and --only-binary force pip to fetch manylinux wheels even on Windows.
      pip install -r "$backend/requirements.txt" -t $build --quiet --no-cache-dir `
        --platform manylinux2014_x86_64 `
        --only-binary=:all: `
        --python-version 3.12 `
        --implementation cp
      Copy-Item -Recurse "$backend/app" "$build/app"
      # Copy all frontend html files
      Get-ChildItem "$backend/../frontend/*.html" | ForEach-Object {
        Copy-Item $_.FullName "$build/$($_.Name)"
      }
      # Copy static assets directory
      if (Test-Path "$backend/../frontend/static") {
        Copy-Item -Recurse "$backend/../frontend/static" "$build/static"
      }
      Write-Host "Lambda build complete."
    EOT
  }
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = local.build_dir
  output_path = "${path.module}/lambda_package.zip"
  depends_on  = [null_resource.lambda_build]
}

# ── IAM ───────────────────────────────────────────────────────────────────────

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.prefix}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "dynamo" {
  name = "${var.prefix}-dynamo-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
      ]
      Resource = [
        var.users_table_arn,
        var.devices_table_arn,
        var.incidents_table_arn,
        var.audit_table_arn,
        "${var.users_table_arn}/index/*",
        "${var.devices_table_arn}/index/*",
        "${var.incidents_table_arn}/index/*",
        "${var.audit_table_arn}/index/*",
      ]
    }]
  })
}

# ── Lambda function ───────────────────────────────────────────────────────────

resource "aws_lambda_function" "api" {
  function_name    = "${var.prefix}-api"
  role             = aws_iam_role.lambda.arn
  handler          = "app.main.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 15
  memory_size      = 256

  environment {
    variables = {
      USERS_TABLE     = var.users_table_name
      DEVICES_TABLE   = var.devices_table_name
      INCIDENTS_TABLE = var.incidents_table_name
      AUDIT_TABLE     = var.audit_table_name
      JWT_SECRET      = var.jwt_secret
      AWS_REGION_NAME = var.aws_region
      BASE_URL        = var.base_url
    }
  }

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.api.function_name}"
  retention_in_days = 14
  tags              = var.tags
}

# ── API Gateway HTTP API ───────────────────────────────────────────────────────
# HTTP API (v2) has lower latency and cost than REST API (v1)

resource "aws_apigatewayv2_api" "main" {
  name          = "${var.prefix}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type"]
    max_age       = 300
  }

  tags = var.tags
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.lambda.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      durationMs     = "$context.integrationLatency"
    })
  }

  tags = var.tags
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
