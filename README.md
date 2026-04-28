# shortlink — URL Shortener

A production-grade URL shortener deployed on AWS, built to demonstrate a real serverless + CDN + DNS stack.

## Architecture

```
Internet
   │
   ▼
Route53 ──── A/AAAA alias ──────────────────────────────┐
                                                         │
                                              ┌──────────▼──────────┐
                                              │      CloudFront      │
                                              │  (CDN + HTTPS/TLS)  │
                                              └──┬──────────────┬───┘
                                    /api/*        │              │  /*
                            ┌───────▼──────┐      │    ┌─────────▼──────┐
                            │ API Gateway  │      │    │   S3 (static   │
                            │  (HTTP API)  │      │    │   frontend)    │
                            └──────┬───────┘      │    └────────────────┘
                                   │
                            ┌──────▼───────┐
                            │    Lambda     │
                            │  (FastAPI +   │
                            │    Mangum)    │
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
| Database | DynamoDB (on-demand billing, PITR enabled) |
| Compute | AWS Lambda |
| API layer | API Gateway HTTP API v2 |
| Frontend | Vanilla HTML/CSS/JS (no build step) |
| CDN | CloudFront (HTTPS, SPA error handling, cache policy) |
| TLS | ACM certificate — DNS-validated, auto-renews |
| DNS | Route53 A + AAAA alias records → CloudFront |
| IaC | Terraform ≥ 1.7, modular layout |
| CI | GitHub Actions — tests + lint on every push |
| CD | GitHub Actions — Terraform apply + S3 sync + cache invalidation on `main` |
| Auth to AWS | OIDC (no long-lived keys stored in GitHub secrets) |

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/links` | Create a short link |
| `GET` | `/api/links/{code}/stats` | View click stats |
| `GET` | `/{code}` | Redirect to original URL (301) |
| `GET` | `/api/docs` | Swagger UI |

### Create a link

```bash
curl -X POST https://yourdomain.com/api/links \
  -H "Content-Type: application/json" \
  -d '{"url": "https://very-long-url.com/...", "custom_code": "gh"}'
# → {"code":"gh","short_url":"https://yourdomain.com/gh","hits":0,...}
```

## Local development

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

# Run tests
pytest

# Start dev server (hot-reload)
uvicorn app.main:app --reload
# API docs → http://localhost:8000/api/docs
```

Open `frontend/index.html` directly in a browser or serve with any static server.

## Deploy to AWS

### Prerequisites

1. AWS account with a Route53 hosted zone for your domain
2. Terraform ≥ 1.7 installed
3. AWS CLI configured (`aws configure`)

### One-time setup

```bash
# Create an S3 bucket for Terraform state (replace with a unique name)
aws s3 mb s3://my-tf-state-shortlink --region ap-northeast-1

# Uncomment the `backend "s3"` block in infrastructure/terraform/main.tf
# and set the bucket name
```

### Provision infrastructure

```bash
cd infrastructure/terraform
terraform init
terraform apply -var="domain_name=short.example.com"
```

Terraform will:
1. Create the DynamoDB table
2. Package and deploy the Lambda function
3. Create API Gateway + Lambda permission
4. Create S3 bucket (private) + Origin Access Control
5. Request ACM certificate and auto-validate it via DNS
6. Create CloudFront distribution with HTTPS + custom domain
7. Create Route53 A + AAAA alias records

### CI/CD (GitHub Actions)

Add these to your repo's **Settings → Secrets and variables**:

| Secret | Value |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | ARN of the IAM role GitHub can assume (OIDC) |

| Variable | Value |
|---|---|
| `DOMAIN_NAME` | Your domain (e.g. `short.example.com`) |

The CD pipeline runs on every push to `main`:
- Runs all tests first (fails fast)
- `terraform apply` to sync infrastructure
- `aws s3 sync` to push frontend assets
- CloudFront cache invalidation

### Setting up GitHub OIDC trust (no stored keys)

```bash
# In AWS IAM → Identity Providers → Add provider
# Provider URL: https://token.actions.githubusercontent.com
# Audience: sts.amazonaws.com

# Then create a role with this trust condition:
# "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:ref:refs/heads/main"
```

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
│       └── dns/             # Route53 + ACM
└── .github/workflows/
    ├── ci.yml               # Test + lint on all branches
    └── cd.yml               # Deploy on push to main
```
