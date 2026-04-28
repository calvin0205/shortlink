from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
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

# Serve the frontend at / when the ../frontend directory exists (local dev only).
# Must be mounted LAST so /api/* and /{code} routes take priority.
_frontend = Path(__file__).parent.parent.parent / "frontend"


@app.get("/{code}", include_in_schema=False)
def redirect_short(code: str):
    """Top-level redirect: GET /<code> → original URL (301)."""
    from fastapi import HTTPException

    item = get_link(code)
    if not item:
        raise HTTPException(status_code=404, detail="Link not found")
    increment_hits(code)
    return RedirectResponse(url=item["url"], status_code=301)


if _frontend.is_dir():
    @app.get("/", include_in_schema=False)
    def serve_index():
        from fastapi.responses import FileResponse
        return FileResponse(str(_frontend / "index.html"))

    app.mount("/", StaticFiles(directory=str(_frontend)), name="frontend")

# AWS Lambda entry point
handler = Mangum(app, lifespan="off")
