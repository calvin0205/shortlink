from fastapi import APIRouter, Depends

from ..dependencies import require_admin
from ..storage.users import _table as users_table

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def list_users(current_user=Depends(require_admin)):
    """Return all users (excluding password_hash), admin only."""
    resp = users_table().scan()
    items = resp.get("Items", [])
    # Exclude password_hash from every user record
    return [
        {k: v for k, v in user.items() if k != "password_hash"}
        for user in items
    ]
