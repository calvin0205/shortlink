from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from botocore.exceptions import ClientError

from ..config import settings
from ..models import CreateLinkRequest, LinkResponse, StatsResponse
from ..shortener import generate_code
from ..storage import code_exists, get_link, increment_hits, put_link

router = APIRouter(prefix="/api/links", tags=["links"])


@router.post("", response_model=LinkResponse, status_code=201)
def create_link(body: CreateLinkRequest) -> LinkResponse:
    url = str(body.url)
    code = body.custom_code or _unique_code()

    if body.custom_code and code_exists(code):
        raise HTTPException(status_code=409, detail="Code already taken")

    try:
        item = put_link(code, url)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise HTTPException(status_code=409, detail="Code collision, retry")
        raise

    return _to_response(item)


@router.get("/{code}/stats", response_model=StatsResponse)
def get_stats(code: str) -> StatsResponse:
    item = get_link(code)
    if not item:
        raise HTTPException(status_code=404, detail="Link not found")
    return _to_response(item)


@router.get("/{code}/redirect")
def redirect(code: str):
    item = get_link(code)
    if not item:
        raise HTTPException(status_code=404, detail="Link not found")
    increment_hits(code)
    return RedirectResponse(url=item["url"], status_code=301)


# ── helpers ──────────────────────────────────────────────────────────────────

def _unique_code() -> str:
    for _ in range(5):
        code = generate_code(settings.code_length)
        if not code_exists(code):
            return code
    raise HTTPException(status_code=503, detail="Could not generate unique code")


def _to_response(item: dict) -> LinkResponse:
    return LinkResponse(
        code=item["code"],
        url=item["url"],
        short_url=f"{settings.base_url}/{item['code']}",
        created_at=item["created_at"],
        hits=int(item.get("hits", 0)),
    )
