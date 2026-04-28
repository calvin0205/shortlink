from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from mangum import Mangum

from .config import settings
from .routes.links import router as links_router
from .storage import get_link, increment_hits

app = FastAPI(title=settings.app_name, version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(links_router)

# index.html locations:
#   local dev  → ../../../frontend/index.html  (relative to this file)
#   Lambda     → ../../index.html              (copied next to app/ in the zip)
_frontend_dir = Path(__file__).parent.parent.parent / "frontend"
_lambda_index = Path(__file__).parent.parent / "index.html"


@app.get("/", include_in_schema=False)
def serve_index():
    if _frontend_dir.is_dir():
        return FileResponse(str(_frontend_dir / "index.html"))
    if _lambda_index.exists():
        return FileResponse(str(_lambda_index))
    raise HTTPException(status_code=404, detail="index.html not found")


@app.get("/{code}", include_in_schema=False)
def redirect_short(code: str):
    """GET /<code> → redirect to original URL (301)."""
    item = get_link(code)
    if not item:
        raise HTTPException(status_code=404, detail="Link not found")
    increment_hits(code)
    return RedirectResponse(url=item["url"], status_code=301)


# Local dev: serve CSS/JS from /static/ (won't conflict with /{code})
if _frontend_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(_frontend_dir)), name="frontend")

# AWS Lambda entry point
handler = Mangum(app, lifespan="off")
