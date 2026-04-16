"""CRUD API for HR policies — viewable & editable by HR / higher_authority."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_hr
from db.connection import get_db_session
from db.models import PolicyModel, UserModel
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/policies", tags=["policies"])


# ── Schemas ───────────────────────────────────────────────────────────────

class PolicyOut(BaseModel):
    id: str
    policy_key: str
    title: str
    content: str
    keywords: str
    is_active: bool
    updated_by: str
    created_at: str | None
    updated_at: str | None


class PolicyCreate(BaseModel):
    policy_key: str = Field(..., min_length=2, max_length=80)
    title: str = Field(..., min_length=2, max_length=200)
    content: str = Field(..., min_length=5)
    keywords: str = ""


class PolicyUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    keywords: str | None = None
    is_active: bool | None = None


# ── Helpers ───────────────────────────────────────────────────────────────

def _to_dict(p: PolicyModel) -> dict:
    return {
        "id": p.id,
        "policy_key": p.policy_key,
        "title": p.title,
        "content": p.content,
        "keywords": p.keywords or "",
        "is_active": p.is_active,
        "updated_by": p.updated_by or "",
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("")
async def list_policies(
    _user: UserModel = Depends(require_hr),
):
    """List all policies (active & inactive)."""
    session = get_db_session()
    try:
        rows = session.query(PolicyModel).order_by(PolicyModel.title).all()
        return [_to_dict(r) for r in rows]
    finally:
        session.close()


@router.get("/{policy_id}")
async def get_policy(
    policy_id: str,
    _user: UserModel = Depends(require_hr),
):
    session = get_db_session()
    try:
        row = session.query(PolicyModel).filter(PolicyModel.id == policy_id).first()
        if not row:
            raise HTTPException(404, "Policy not found")
        return _to_dict(row)
    finally:
        session.close()


@router.post("", status_code=201)
async def create_policy(
    body: PolicyCreate,
    user: UserModel = Depends(require_hr),
):
    """Create a new policy entry."""
    session = get_db_session()
    try:
        existing = (
            session.query(PolicyModel)
            .filter(PolicyModel.policy_key == body.policy_key)
            .first()
        )
        if existing:
            raise HTTPException(409, f"Policy key '{body.policy_key}' already exists")

        policy = PolicyModel(
            id=str(uuid.uuid4()),
            policy_key=body.policy_key,
            title=body.title,
            content=body.content,
            keywords=body.keywords,
            is_active=True,
            updated_by=user.username,
        )
        session.add(policy)
        session.commit()
        session.refresh(policy)
        logger.info(f"Policy created: {policy.policy_key} by {user.username}")
        return _to_dict(policy)
    finally:
        session.close()


@router.patch("/{policy_id}")
async def update_policy(
    policy_id: str,
    body: PolicyUpdate,
    user: UserModel = Depends(require_hr),
):
    """Update an existing policy."""
    session = get_db_session()
    try:
        row = session.query(PolicyModel).filter(PolicyModel.id == policy_id).first()
        if not row:
            raise HTTPException(404, "Policy not found")

        if body.title is not None:
            row.title = body.title
        if body.content is not None:
            row.content = body.content
        if body.keywords is not None:
            row.keywords = body.keywords
        if body.is_active is not None:
            row.is_active = body.is_active

        row.updated_by = user.username
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(row)
        logger.info(f"Policy updated: {row.policy_key} by {user.username}")
        return _to_dict(row)
    finally:
        session.close()


@router.delete("/{policy_id}")
async def delete_policy(
    policy_id: str,
    user: UserModel = Depends(require_hr),
):
    """Permanently delete a policy."""
    session = get_db_session()
    try:
        row = session.query(PolicyModel).filter(PolicyModel.id == policy_id).first()
        if not row:
            raise HTTPException(404, "Policy not found")
        session.delete(row)
        session.commit()
        logger.info(f"Policy deleted: {row.policy_key} by {user.username}")
        return {"deleted": True}
    finally:
        session.close()


@router.post("/seed")
async def seed_policies(
    user: UserModel = Depends(require_hr),
):
    """Seed the DB with default policies from the hardcoded knowledge base.

    Only inserts policies whose ``policy_key`` doesn't already exist, so it's
    safe to call multiple times.
    """
    from agents.policy.tools import _POLICIES, _KEYWORD_MAP

    session = get_db_session()
    try:
        inserted = 0
        for key, content in _POLICIES.items():
            exists = (
                session.query(PolicyModel)
                .filter(PolicyModel.policy_key == key)
                .first()
            )
            if exists:
                continue

            title = key.replace("_", " ").title()
            kw = ", ".join(_KEYWORD_MAP.get(key, []))
            policy = PolicyModel(
                id=str(uuid.uuid4()),
                policy_key=key,
                title=title,
                content=content,
                keywords=kw,
                is_active=True,
                updated_by="system",
            )
            session.add(policy)
            inserted += 1

        session.commit()
        logger.info(f"Seed: inserted {inserted} policies")
        return {"inserted": inserted}
    finally:
        session.close()
