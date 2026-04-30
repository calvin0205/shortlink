# shortlink — URL Shortener

A production-grade URL shortener deployed on AWS, built on a serverless + CDN stack.

**Live site:** https://d37632ffxb5y05.cloudfront.net

## Architecture

```
Internet
   │
   ▼
┌──────────────────────┐
│      CloudFront      │
│  (CDN + HTTPS/TLS)   │
└──┬───────────────┬───┘
   │ /static/*     │ /* and /api/*
   ▼               ▼
┌──────────┐  ┌──────────────┐
│ S3       │  │ API Gateway  │
│ (CSS/JS) │  │  (HTTP API)  │
└──────────┘  └──────┬───────┘
                     │
              ┌──────▼───────┐
              │    Lambda    │
              │ (FastAPI +   │
              │   Mangum)    │
              └──────┬───────┘
                     │
              ┌──────▼───────┐
              │   DynamoDB   │
              └──────────────┘
```

## What's in the box

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Mangum (Lambda adapter) |
| Database | DynamoDB (on-demand billing) |
| Compute | AWS Lambda |
| API layer | API Gateway HTTP API v2 |
| Frontend | Vanilla HTML/CSS/JS (no build step) |
| CDN | CloudFront (HTTPS, cache policy) |
| TLS | CloudFront default certificate (HTTPS out of the box) |
| IaC | Terraform ≥ 1.7, modular layout |
| CI | GitHub Actions — tests + lint on every push |

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/links` | Create a short link |
| `GET` | `/api/links/{code}/stats` | View click stats |
| `GET` | `/{code}` | Redirect to original URL (301) |
| `GET` | `/api/docs` | Swagger UI |

### Create a link

```bash
curl -X POST https://d37632ffxb5y05.cloudfront.net/api/links \
  -H "Content-Type: application/json" \
  -d '{"url": "https://very-long-url.com/...", "custom_code": "gh"}'
# → {"code":"gh","short_url":"https://d37632ffxb5y05.cloudfront.net/gh","hits":0,...}
```

## Local development

### Prerequisites

- Python 3.12+
- Docker (for DynamoDB Local)

### Setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```

### Start dev server

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev-start.ps1
```

This will:
1. Start DynamoDB Local in Docker on port 8001
2. Create the local DynamoDB table
3. Start the FastAPI server at http://localhost:8000

API docs → http://localhost:8000/api/docs

### Run tests

```powershell
cd backend
pytest
```

Tests use `moto` to mock DynamoDB — no real AWS credentials needed.

## Deploy to AWS

### Prerequisites

1. AWS account
2. Terraform ≥ 1.7
3. AWS CLI configured (`aws configure`)

### Provision infrastructure

```powershell
cd infrastructure/terraform
terraform init
terraform apply -auto-approve
```

After the first apply, set `base_url_override` to the CloudFront URL shown in the output:

```powershell
terraform apply "-var=base_url_override=https://xxxxx.cloudfront.net" -auto-approve
```

### Upload frontend assets

```powershell
aws s3 sync frontend\ s3://<s3_frontend_bucket>/static/ --exclude "*.html"
aws cloudfront create-invalidation --distribution-id <cloudfront_distribution_id> --paths "/*"
```

Replace `<s3_frontend_bucket>` and `<cloudfront_distribution_id>` with values from `terraform output`.

## Project structure

```
shortlink/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app + Lambda handler
│   │   ├── config.py        # Settings (pydantic-settings)
│   │   ├── models.py        # Pydantic request/response models
│   │   ├── shortener.py     # Code generation logic
│   │   ├── storage.py       # DynamoDB operations
│   │   └── routes/links.py  # API routes
│   ├── tests/               # pytest + moto (no real AWS needed)
│   └── requirements*.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── infrastructure/terraform/
│   ├── main.tf              # Root module
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/
│       ├── storage/         # DynamoDB
│       ├── api/             # Lambda + API Gateway
│       ├── frontend/        # S3 + CloudFront
│       └── dns/             # Route53 + ACM (optional, for custom domain)
├── scripts/
│   ├── dev-start.ps1        # One-command local dev startup
│   └── create-table.py      # Creates DynamoDB table locally
└── .github/workflows/
    ├── ci.yml               # Test + lint on all branches
    └── cd.yml               # Deploy on push to main
```
