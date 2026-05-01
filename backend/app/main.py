from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from mangum import Mangum

from .config import settings
from .routes import auth, devices, incidents, dashboard
from .routes import audit as audit_router
from .routes import simulate as simulate_router
from .routes import admin as admin_router
from .routes import assistant as assistant_router
from .routes import metrics as metrics_router

app = FastAPI(
    title="OT Sentinel",
    version="1.0.0",
    description="""
## OT/IoT Security Monitoring Platform

OT Sentinel is a serverless security monitoring platform for Operational Technology (OT) and IoT devices in industrial environments.

### Features
- 🔐 **JWT Authentication** with role-based access control (Admin / Operator)
- 🖥️ **Device Inventory** with real-time status monitoring
- ⚠️ **Incident Management** with severity-based risk scoring
- ⚡ **Anomaly Simulation** — trigger security events for demo/testing
- 🤖 **AI Assistant** with OT/ICS security knowledge base
- 📋 **Audit Logging** for compliance and forensics

### Architecture
- **Compute**: AWS Lambda (Python 3.12 + FastAPI + Mangum)
- **Database**: DynamoDB with GSI for efficient queries
- **CDN**: CloudFront (HTTPS, cache optimization)
- **Frontend**: Vanilla HTML/CSS/JS served via Lambda

### Authentication
All endpoints (except health check) require a Bearer token obtained from `POST /api/auth/login`.
""",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_tags=[
        {"name": "auth", "description": "Authentication and user management"},
        {"name": "devices", "description": "OT/IoT device inventory and status"},
        {"name": "incidents", "description": "Security incident management and lifecycle"},
        {"name": "dashboard", "description": "Summary statistics and overview"},
        {"name": "assistant", "description": "AI-powered security analysis"},
        {"name": "audit", "description": "Audit log for compliance and forensics"},
        {"name": "admin", "description": "Admin-only operations (requires admin role)"},
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
# simulate router must be included BEFORE devices router to avoid path collision
# (/api/devices/anomaly-types would be captured as {device_id} otherwise)
app.include_router(simulate_router.router)
# metrics router must be included BEFORE devices router so /{device_id}/metrics
# is not shadowed by the /{device_id} catch-all in the devices router
app.include_router(metrics_router.router)
app.include_router(devices.router)
app.include_router(incidents.router)
app.include_router(dashboard.router)
app.include_router(audit_router.router)
app.include_router(admin_router.router)
app.include_router(assistant_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


_frontend_dir = Path(__file__).parent.parent.parent / "frontend"
_lambda_dir = Path(__file__).parent.parent

if _frontend_dir.is_dir():
    _static_dir = _frontend_dir / "static"
    if _static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str = ""):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404)
    # Try to serve exact .html file requested
    for base in [_frontend_dir, _lambda_dir]:
        if not base.is_dir() and not base.exists():
            continue
        if full_path:
            target = base / full_path
            if target.exists():
                return FileResponse(str(target))
            html_target = base / (full_path + ".html")
            if html_target.exists():
                return FileResponse(str(html_target))
        index = base / "index.html"
        if index.exists():
            return FileResponse(str(index))
    raise HTTPException(status_code=404, detail="Page not found")


# AWS Lambda entry point
_mangum = Mangum(app, lifespan="off")


def handler(event, context):
    # EventBridge scheduled events carry source="aws.events"
    if event.get("source") == "aws.events":
        from app.simulator import run_heartbeat
        result = run_heartbeat()
        return {"statusCode": 200, "body": str(result)}
    return _mangum(event, context)
