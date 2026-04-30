# 🛡️ OT Sentinel

> A production-grade OT/IoT security monitoring platform built on AWS serverless architecture.
> Designed to demonstrate real-world DevSecOps practices for industrial cybersecurity.

**Live Demo**: https://d37632ffxb5y05.cloudfront.net  
**API Docs**: https://d37632ffxb5y05.cloudfront.net/api/docs

---

## Architecture

```
                        ┌─────────────────────────────────────────────┐
                        │              CloudFront (CDN + HTTPS)        │
                        │         Certificate: ACM (auto-renew)        │
                        └──────┬──────────────┬────────────────────────┘
                               │ /static/*    │ /api/* and /*
                               ▼              ▼
                        ┌──────────┐   ┌──────────────────────┐
                        │  S3      │   │   API Gateway v2     │
                        │ (CSS/JS) │   │   (HTTP API)         │
                        └──────────┘   └──────────┬───────────┘
                                                   │
                                          ┌────────▼─────────┐
                                          │  AWS Lambda      │
                                          │  Python 3.12     │
                                          │  FastAPI+Mangum  │
                                          └────────┬─────────┘
                                                   │
                              ┌────────────────────┴──────────────────┐
                              │            DynamoDB (4 tables)         │
                              │  users  devices  incidents  audit      │
                              │  (with GSI for efficient queries)      │
                              └───────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Mangum (Lambda adapter) |
| Database | AWS DynamoDB (PAY_PER_REQUEST, GSI) |
| Compute | AWS Lambda (512MB, 15s timeout) |
| API | AWS API Gateway HTTP API v2 |
| Frontend | Vanilla HTML/CSS/JS + Chart.js |
| CDN | AWS CloudFront (HTTPS, cache policies) |
| Auth | JWT (python-jose + bcrypt) + RBAC |
| IaC | Terraform ≥ 1.7 (modular) |
| CI | GitHub Actions — test + lint + security scan |
| CD | GitHub Actions — Terraform + S3 sync via OIDC |

## Features

### Phase 1 — Full-Stack Skeleton ✅
- JWT login with RBAC (Admin / Operator roles)
- Dashboard with Chart.js visualizations
- Device inventory with status monitoring
- Incident management table
- Audit log (admin only)
- DynamoDB seed data (10 devices, 15 incidents, 20 audit logs)

### Phase 2 — Security Vertical Slice ✅
- **Anomaly Simulation** — trigger 10 types of OT security events
- **Risk Scoring Engine** — score 0-100 based on anomaly type × device type multiplier
- **Incident Lifecycle** — Open → Investigating → Resolved
- **Device Status Updates** — automatic status degradation on incident
- **Audit Logging** — every action recorded with user, IP, timestamp
- **RBAC** — admin-only routes, operator restrictions

### Phase 3 — AI Assistant ✅
- Rule-based OT/ICS knowledge base (10 threat categories)
- Incident context injection — AI analyzes specific incidents
- Standards references: IEC 62443, NIST SP 800-82, MITRE ATT&CK for ICS
- Optional LLM integration via `ANTHROPIC_API_KEY`
- Suggested queries for quick exploration

### Phase 4 — DevSecOps Polish ✅
- GitHub Actions CI: pytest (70% coverage), ruff lint, bandit security scan
- GitHub Actions CD: Terraform apply + S3 sync via AWS OIDC (no stored keys)
- Comprehensive API documentation (Swagger + ReDoc)
- Threat model (STRIDE)
- Architecture diagram

## DynamoDB Schema

```
users table
├── PK: "USER#{uuid}"
├── email, name, role, password_hash, created_at
└── GSI: email-index (email → PK)

devices table
├── PK: "DEVICE#{uuid}"
├── name, type, site_id, site_name, status, ip_address, firmware_version, last_seen, risk_score
├── GSI: status-index (status + last_seen)
└── GSI: site-index (site_id + PK)

incidents table
├── PK: "INCIDENT#{uuid}"
├── device_id, device_name, severity, status, title, description, risk_score, created_at, resolved_at
├── GSI: device-index (device_id + created_at)
└── GSI: severity-index (severity + created_at)

audit table
├── PK: "LOG#{uuid}"
├── user_id, user_email, action, resource_type, resource_id, detail, ip_address, timestamp
└── GSI: user-index (user_id + timestamp)
```

## Risk Scoring

Risk scores (0–100) are calculated as:

```
risk_score = base_score(anomaly_type) × multiplier(device_type)
```

| Anomaly Type | Base Score Range |
|---|---|
| Unauthorized Access | 82–96 |
| Sensor Manipulation | 78–94 |
| Firmware Tampering | 78–92 |
| Brute Force | 72–88 |
| Protocol Anomaly | 68–84 |
| Config Change | 62–78 |
| Unusual Traffic | 52–68 |
| Network Scan | 55–72 |
| Memory Overflow | 42–58 |
| Comm Timeout | 35–52 |

| Device Type | Multiplier |
|---|---|
| PLC | 1.20× |
| RTU | 1.15× |
| HMI | 1.10× |
| Gateway | 1.05× |
| Sensor | 1.00× |

**Severity**: Critical ≥80 · High 60–79 · Medium 40–59 · Low <40

## Threat Model (STRIDE)

| Threat | Vector | Mitigation |
|---|---|---|
| **Spoofing** | Forged JWT tokens | JWT signature validation, short expiry (8h), bcrypt password hashing |
| **Tampering** | Modifying DynamoDB items directly | IAM least-privilege, Lambda role restricted to specific table ARNs |
| **Repudiation** | Denying actions performed | Immutable audit log with user_id, IP, timestamp on every action |
| **Information Disclosure** | Exposing sensitive data via API | RBAC — audit log admin-only, password_hash never returned in responses |
| **Denial of Service** | Lambda cold start abuse | CloudFront rate limiting, API Gateway throttling |
| **Elevation of Privilege** | Operator accessing admin routes | `require_admin` dependency enforced at route level, role embedded in JWT |

## Local Development

### Prerequisites
- Python 3.12+
- Docker Desktop

### Setup
```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements-dev.txt
```

### Start dev server
```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev-start.ps1
```

Opens at http://localhost:8000/login.html

**Credentials:**
- Admin: `admin@otsentinel.com` / `Admin1234!`
- Operator: `operator@otsentinel.com` / `Oper1234!`

### Run tests
```powershell
cd backend
.venv\Scripts\pytest.exe --cov=app
```

## Deploy to AWS

### Prerequisites
1. AWS account + AWS CLI configured
2. Terraform ≥ 1.7

### First deploy
```powershell
cd infrastructure/terraform
terraform init
terraform apply -auto-approve
# Note the cloudfront URL from output, then:
terraform apply -var="base_url_override=https://xxxxx.cloudfront.net" -auto-approve
```

### Upload frontend
```powershell
aws s3 sync frontend\ s3://<s3_frontend_bucket>\static\ --exclude "*.html"
aws cloudfront create-invalidation --distribution-id <cf_id> --paths "/*"
```

### CI/CD Setup (GitHub Actions)
Add to repo Settings → Secrets:
- `AWS_DEPLOY_ROLE_ARN` — IAM role with OIDC trust for GitHub Actions
- `JWT_SECRET` — production JWT signing secret

Add to repo Settings → Variables:
- `CLOUDFRONT_URL` — e.g. `https://xxxxx.cloudfront.net`

## Project Structure

```
ot-sentinel/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + Lambda handler
│   │   ├── auth.py              # JWT utilities (python-jose + bcrypt)
│   │   ├── dependencies.py      # get_current_user, require_admin
│   │   ├── risk_engine.py       # Risk scoring engine (10 anomaly types)
│   │   ├── ai_engine.py         # Rule-based AI + optional Claude LLM
│   │   ├── config.py            # pydantic-settings configuration
│   │   ├── models/              # Pydantic request/response models
│   │   ├── routes/              # API route handlers
│   │   └── storage/             # DynamoDB operations
│   ├── tests/                   # pytest + moto (no real AWS needed)
│   └── requirements*.txt
├── frontend/
│   ├── *.html                   # 7 pages (login, dashboard, devices...)
│   └── static/                  # CSS + per-page JS
├── infrastructure/terraform/
│   ├── main.tf                  # Root module
│   └── modules/
│       ├── storage/             # DynamoDB (4 tables, 7 GSIs)
│       ├── api/                 # Lambda + API Gateway
│       └── frontend/            # S3 + CloudFront
├── scripts/
│   ├── dev-start.ps1            # One-command local startup
│   ├── seed-data.py             # Seed DynamoDB with demo data
│   └── create-table.py          # Create local DynamoDB tables
└── .github/workflows/
    ├── ci.yml                   # Test + Lint + Security scan
    └── cd.yml                   # Deploy on push to master
```
