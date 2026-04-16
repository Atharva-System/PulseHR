"""Auth API routes — login, refresh, me, change-password, reset-password."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    require_hr,
    verify_password,
    verify_token,
)
from db.connection import get_db_session
from db.models import UserModel
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=4)


class ResetPasswordRequest(BaseModel):
    username: str = Field(..., min_length=2)
    new_password: str = Field(..., min_length=4)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Authenticate user and return JWT tokens."""
    session = get_db_session()
    try:
        user = (
            session.query(UserModel)
            .filter_by(username=body.username)
            .first()
        )
        if user is None or not verify_password(body.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact your administrator.",
            )

        access_token = create_access_token(user.id, user.role)
        refresh_token = create_refresh_token(user.id, user.role)

        # Track login timestamps: shift current -> previous, set new current
        user.previous_login = user.last_login
        user.last_login = datetime.now(timezone.utc)
        session.commit()
        session.refresh(user)

        logger.info(f"User '{user.username}' logged in (role={user.role})")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user.to_dict(),
        )
    finally:
        session.close()


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(body: RefreshRequest):
    """Exchange a valid refresh token for a new access token."""
    payload = verify_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — refresh token required",
        )

    user_id = payload.get("sub")
    role = payload.get("role")

    # Verify user still exists and is active
    session = get_db_session()
    try:
        user = session.query(UserModel).filter_by(id=user_id, is_active=True).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or deactivated",
            )
        # Use fresh role from DB (in case it changed)
        access_token = create_access_token(user.id, user.role)
        return RefreshResponse(access_token=access_token)
    finally:
        session.close()


@router.get("/me")
async def me(current_user: UserModel = Depends(get_current_user)):
    """Return profile of the currently authenticated user."""
    return current_user.to_dict()


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Change the current user's password."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    session = get_db_session()
    try:
        user = session.query(UserModel).filter_by(id=current_user.id).first()
        user.password_hash = hash_password(body.new_password)
        session.commit()
        logger.info(f"User '{current_user.username}' changed password")
        return {"message": "Password changed successfully"}
    finally:
        session.close()


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    current_user: UserModel = Depends(require_hr),
):
    """Reset a user's password. HR and Higher Authority only.

    This allows HR to reset passwords for employees who forgot theirs.
    """
    session = get_db_session()
    try:
        user = session.query(UserModel).filter_by(username=body.username).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        # HR can only reset user passwords; authority can reset anyone except other authority
        if current_user.role == "hr" and user.role != "user":
            raise HTTPException(status_code=403, detail="HR can only reset user passwords")
        if user.role == "higher_authority" and current_user.id != user.id:
            raise HTTPException(status_code=403, detail="Cannot reset another authority's password")

        user.password_hash = hash_password(body.new_password)
        session.commit()
        logger.info(f"Password reset for '{body.username}' by '{current_user.username}'")
        return {"message": f"Password for '{body.username}' has been reset successfully"}
    finally:
        session.close()
