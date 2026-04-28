#!/usr/bin/env bash
# One-command local dev startup:
#   1. Starts DynamoDB Local in Docker
#   2. Creates the table (idempotent)
#   3. Starts uvicorn with HTTPS
#
# Usage: bash scripts/dev-start.sh

set -euo pipefail

CERT_DIR="backend/certs"
TABLE="shortlink-links"
DYNAMO_PORT=8001
API_PORT=8000

# ── 1. Start DynamoDB Local ───────────────────────────────────────────────────
echo "→ Starting DynamoDB Local on port $DYNAMO_PORT…"
docker run -d --rm \
  --name shortlink-dynamo \
  -p ${DYNAMO_PORT}:8000 \
  amazon/dynamodb-local:latest \
  -jar DynamoDBLocal.jar -inMemory \
  2>/dev/null || echo "  (already running)"

sleep 1  # give DynamoDB Local a moment to be ready

# ── 2. Create table (skip if already exists) ──────────────────────────────────
echo "→ Creating DynamoDB table '$TABLE'…"
aws dynamodb create-table \
  --endpoint-url http://localhost:${DYNAMO_PORT} \
  --table-name "$TABLE" \
  --attribute-definitions AttributeName=code,AttributeType=S \
  --key-schema AttributeName=code,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-northeast-1 \
  --no-cli-pager \
  2>/dev/null && echo "  Table created." || echo "  Table already exists, skipping."

# ── 3. Start uvicorn ──────────────────────────────────────────────────────────
cd backend

if [[ -f "certs/cert.pem" ]]; then
  echo "→ Starting HTTPS server on https://localhost:${API_PORT} …"
  echo ""
  DYNAMODB_ENDPOINT_URL=http://localhost:${DYNAMO_PORT} \
  uvicorn app.main:app --reload \
    --port ${API_PORT} \
    --ssl-keyfile certs/key.pem \
    --ssl-certfile certs/cert.pem
else
  echo "→ No certs found — starting HTTP server on http://localhost:${API_PORT}"
  echo "  (run 'bash scripts/gen-dev-certs.sh' to enable HTTPS)"
  echo ""
  DYNAMODB_ENDPOINT_URL=http://localhost:${DYNAMO_PORT} \
  uvicorn app.main:app --reload --port ${API_PORT}
fi
