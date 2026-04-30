# One-command local dev startup (Windows PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File scripts\dev-start.ps1

$ErrorActionPreference = "Stop"

$DYNAMO_PORT  = 8001
$API_PORT     = 8000
$ROOT         = Split-Path $PSScriptRoot -Parent
$CONTAINER    = "otsentinel-dynamo"

Set-Location $ROOT

# ── 1. Start DynamoDB Local ───────────────────────────────────────────────────
Write-Host "-> Starting DynamoDB Local on port $DYNAMO_PORT..." -ForegroundColor Cyan

$existing = docker ps --filter "name=$CONTAINER" --format "{{.Names}}"
if ($existing -eq $CONTAINER) {
    Write-Host "   (already running)"
} else {
    docker run -d --rm `
        --name $CONTAINER `
        -p "${DYNAMO_PORT}:8000" `
        amazon/dynamodb-local:latest `
        -jar DynamoDBLocal.jar -inMemory | Out-Null
    Write-Host "   Started."
    Start-Sleep -Seconds 2
}

# ── 2. Activate venv ─────────────────────────────────────────────────────────
$venvActivate = "$ROOT\backend\.venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "-> Activating virtual environment..." -ForegroundColor Cyan
    & $venvActivate
} else {
    Write-Host "WARNING: .venv not found. Run: cd backend; python -m venv .venv; .venv\Scripts\activate; pip install -r requirements-dev.txt" -ForegroundColor Yellow
}

# ── 3. Set environment variables ──────────────────────────────────────────────
$env:DYNAMODB_ENDPOINT_URL = "http://localhost:$DYNAMO_PORT"
$env:USERS_TABLE           = "otsentinel-prod-users"
$env:DEVICES_TABLE         = "otsentinel-prod-devices"
$env:INCIDENTS_TABLE       = "otsentinel-prod-incidents"
$env:AUDIT_TABLE           = "otsentinel-prod-audit"
$env:JWT_SECRET            = "dev-secret-change-in-prod"
$env:AWS_DEFAULT_REGION    = "ap-northeast-1"
$env:AWS_ACCESS_KEY_ID     = "local"
$env:AWS_SECRET_ACCESS_KEY = "local"

# ── 4. Create DynamoDB tables ─────────────────────────────────────────────────
Write-Host "-> Creating DynamoDB tables..." -ForegroundColor Cyan
python "$ROOT\scripts\create-table.py"

# ── 5. Seed data ──────────────────────────────────────────────────────────────
Write-Host "-> Seeding data..." -ForegroundColor Cyan
python "$ROOT\scripts\seed-data.py"

# ── 6. Start uvicorn ──────────────────────────────────────────────────────────
Set-Location "$ROOT\backend"

Write-Host "`n-> Starting HTTP server at http://localhost:$API_PORT" -ForegroundColor Green
Write-Host "   API docs: http://localhost:$API_PORT/api/docs"
Write-Host "   Login at: http://localhost:$API_PORT/login.html"
Write-Host "   Credentials: admin@otsentinel.com / Admin1234!`n"

uvicorn app.main:app --reload --port $API_PORT
