from fastapi import APIRouter, Depends, HTTPException

from ..auth import create_access_token, verify_password
from ..dependencies import get_current_user
from ..models.auth import LoginRequest, TokenResponse
from ..storage.users import get_user_by_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """Authenticate with email and password. Returns a JWT Bearer token valid for 8 hours."""
    user = get_user_by_email(body.email)
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user["user_id"], "email": user["email"], "role": user["role"]})

    safe_user = {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    }
    return TokenResponse(access_token=token, user=safe_user)


@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return {
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "role": current_user["role"],
    }
