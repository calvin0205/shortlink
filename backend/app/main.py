from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from mangum import Mangum

from .config import settings
from .routes import auth, devices, incidents, dashboard
from .routes import audit as audit_router

app = FastAPI(title=settings.app_name, version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(devices.router)
app.include_router(incidents.router)
app.include_router(dashboard.router)
app.include_router(audit_router.router)


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
handler = Mangum(app, lifespan="off")
