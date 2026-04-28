# One-command local dev startup (Windows PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File scripts\dev-start.ps1

$ErrorActionPreference = "Stop"

$TABLE      = "shortlink-links"
$DYNAMO_PORT = 8001
$API_PORT    = 8000
$ROOT        = Split-Path $PSScriptRoot -Parent

Set-Location $ROOT

# ── 1. Start DynamoDB Local ───────────────────────────────────────────────────
Write-Host "-> Starting DynamoDB Local on port $DYNAMO_PORT..." -ForegroundColor Cyan

$existing = docker ps --filter "name=shortlink-dynamo" --format "{{.Names}}"
if ($existing -eq "shortlink-dynamo") {
    Write-Host "   (already running)"
} else {
    docker run -d --rm `
        --name shortlink-dynamo `
        -p "${DYNAMO_PORT}:8000" `
        amazon/dynamodb-local:latest `
        -jar DynamoDBLocal.jar -inMemory | Out-Null
    Write-Host "   Started."
    Start-Sleep -Seconds 2
}

# ── 2. Activate venv ─────────────────────────────────────────────────────────
# (needed before step 3 so Python/boto3 is available)
$venvActivate = "$ROOT\backend\.venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    Write-Host "-> Activating virtual environment..." -ForegroundColor Cyan
    & $venvActivate
} else {
    Write-Host "WARNING: .venv not found. Run: cd backend; python -m venv .venv; .venv\Scripts\activate; pip install -r requirements-dev.txt" -ForegroundColor Yellow
}

# ── 3. Create DynamoDB table (uses Python/boto3, no AWS CLI needed) ───────────
Write-Host "-> Creating DynamoDB table '$TABLE'..." -ForegroundColor Cyan
python "$ROOT\scripts\create-table.py"

# ── 4. Start uvicorn ──────────────────────────────────────────────────────────
$env:DYNAMODB_ENDPOINT_URL = "http://localhost:$DYNAMO_PORT"
$certKey  = "$ROOT\backend\certs\key.pem"
$certFile = "$ROOT\backend\certs\cert.pem"

Set-Location "$ROOT\backend"

if ((Test-Path $certKey) -and (Test-Path $certFile)) {
    Write-Host "-> Starting HTTPS server at https://localhost:$API_PORT" -ForegroundColor Green
    Write-Host "   API docs: https://localhost:$API_PORT/api/docs`n"
    uvicorn app.main:app --reload --port $API_PORT `
        --ssl-keyfile "certs\key.pem" `
        --ssl-certfile "certs\cert.pem"
} else {
    Write-Host "-> Starting HTTP server at http://localhost:$API_PORT" -ForegroundColor Green
    Write-Host "   API docs: http://localhost:$API_PORT/api/docs`n"
    uvicorn app.main:app --reload --port $API_PORT
}
