"""User management API routes — CRUD for users by HR / Higher Authority."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, EmailStr

from app.auth import get_current_user, hash_password, require_hr, require_authority
from db.connection import get_db_session
from db.models import UserModel
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    email: str = Field(..., max_length=120)
    full_name: str = Field("", max_length=120)
    password: str = Field(..., min_length=4)
    role: str = Field("user", pattern="^(user|hr|higher_authority)$")
    receive_notifications: bool = False
    notification_levels: Optional[list[str]] = None


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = Field(None, pattern="^(user|hr|higher_authority)$")
    receive_notifications: Optional[bool] = None
    notification_levels: Optional[list[str]] = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    receive_notifications: bool = False
    notification_levels: list[str] = ["critical", "high", "medium", "low"]
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Create a new user account.

    - HR can create 'user' role accounts only.
    - Higher Authority can create 'user' and 'hr' role accounts.
    """
    # Role-based permission check
    if current_user.role == "user":
        raise HTTPException(status_code=403, detail="Users cannot create accounts")

    if current_user.role == "hr" and body.role != "user":
        raise HTTPException(
            status_code=403,
            detail="HR can only create 'user' accounts",
        )

    if current_user.role == "higher_authority" and body.role == "higher_authority":
        raise HTTPException(
            status_code=403,
            detail="Cannot create another higher_authority account",
        )

    session = get_db_session()
    try:
        # Check duplicates
        existing = session.query(UserModel).filter(
            (UserModel.username == body.username) | (UserModel.email == body.email)
        ).first()
        if existing:
            field = "username" if existing.username == body.username else "email"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A user with this {field} already exists",
            )

        user = UserModel(
            id=str(uuid.uuid4()),
            username=body.username,
            email=body.email,
            full_name=body.full_name,
            password_hash=hash_password(body.password),
            role=body.role,
            is_active=True,
            receive_notifications=body.receive_notifications,
            created_by=current_user.id,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        logger.info(
            f"User '{body.username}' (role={body.role}) created by "
            f"'{current_user.username}'"
        )
        return UserResponse(**user.to_dict())
    finally:
        session.close()


@router.get("", response_model=list[UserResponse])
async def list_users(
    role: Optional[str] = Query(None, pattern="^(user|hr|higher_authority)$"),
    is_active: Optional[bool] = Query(None),
    current_user: UserModel = Depends(require_hr),
):
    """List users with optional filters. HR and Higher Authority only."""
    session = get_db_session()
    try:
        q = session.query(UserModel)
        if role:
            q = q.filter_by(role=role)
        if is_active is not None:
            q = q.filter_by(is_active=is_active)
        q = q.order_by(UserModel.created_at.desc())
        users = q.all()
        return [UserResponse(**u.to_dict()) for u in users]
    finally:
        session.close()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: UserModel = Depends(require_hr),
):
    """Get a single user by ID. HR and Higher Authority only."""
    session = get_db_session()
    try:
        user = session.query(UserModel).filter_by(id=user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(**user.to_dict())
    finally:
        session.close()


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    current_user: UserModel = Depends(require_authority),
):
    """Update a user. Higher Authority only."""
    session = get_db_session()
    try:
        user = session.query(UserModel).filter_by(id=user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        if body.full_name is not None:
            user.full_name = body.full_name
        if body.email is not None:
            user.email = body.email
        if body.is_active is not None:
            user.is_active = body.is_active
        if body.role is not None:
            if body.role == "higher_authority":
                raise HTTPException(status_code=403, detail="Cannot assign higher_authority role")
            user.role = body.role
        if body.receive_notifications is not None:
            user.receive_notifications = body.receive_notifications
        if body.notification_levels is not None:
            valid = {"critical", "high", "medium", "low"}
            levels = [l for l in body.notification_levels if l in valid]
            user.notification_levels = ",".join(levels) if levels else ""

        session.commit()
        session.refresh(user)
        logger.info(f"User '{user.username}' updated by '{current_user.username}'")
        return UserResponse(**user.to_dict())
    finally:
        session.close()


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user: UserModel = Depends(require_authority),
):
    """Soft-delete (deactivate) a user. Higher Authority only."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    session = get_db_session()
    try:
        user = session.query(UserModel).filter_by(id=user_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_active = False
        session.commit()
        logger.info(f"User '{user.username}' deactivated by '{current_user.username}'")
        return {"message": f"User '{user.username}' has been deactivated"}
    finally:
        session.close()
