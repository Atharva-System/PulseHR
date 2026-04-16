"""Conversation API routes — view chat history for HR / Higher Authority."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import require_hr
from db.connection import get_db_session
from db.models import ConversationModel, UserModel
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ConversationResponse(BaseModel):
    entry_id: str
    user_id: str
    message: str
    response: str
    intent: str
    emotion: str
    severity: str
    agent_used: str
    trace_id: str
    timestamp: Optional[str] = None


class ConversationStatsResponse(BaseModel):
    total_messages: int
    unique_users: int
    by_intent: dict
    by_agent: dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _conv_to_dict(c: ConversationModel) -> dict:
    return {
        "entry_id": c.entry_id,
        "user_id": c.user_id or "",
        "message": c.message or "",
        "response": c.response or "",
        "intent": c.intent or "",
        "emotion": c.emotion or "",
        "severity": c.severity or "",
        "agent_used": c.agent_used or "",
        "trace_id": c.trace_id or "",
        "timestamp": c.timestamp.isoformat() if c.timestamp else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    user_id: Optional[str] = Query(None),
    intent: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: UserModel = Depends(require_hr),
):
    """List conversations with filters and pagination. HR and Authority only."""
    from datetime import datetime

    session = get_db_session()
    try:
        q = session.query(ConversationModel)
        if user_id:
            q = q.filter(ConversationModel.user_id == user_id)
        if intent:
            q = q.filter(ConversationModel.intent == intent)
        if date_from:
            q = q.filter(ConversationModel.timestamp >= datetime.fromisoformat(date_from))
        if date_to:
            q = q.filter(
                ConversationModel.timestamp <= datetime.fromisoformat(date_to + "T23:59:59")
            )

        conversations = (
            q.order_by(ConversationModel.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [ConversationResponse(**_conv_to_dict(c)) for c in conversations]
    finally:
        session.close()


@router.get("/users")
async def list_conversation_users(
    current_user: UserModel = Depends(require_hr),
):
    """List all users who have conversations, with their message counts."""
    from sqlalchemy import func

    session = get_db_session()
    try:
        rows = (
            session.query(
                ConversationModel.user_id,
                func.count(ConversationModel.entry_id).label("message_count"),
                func.max(ConversationModel.timestamp).label("last_message_at"),
            )
            .group_by(ConversationModel.user_id)
            .order_by(func.max(ConversationModel.timestamp).desc())
            .all()
        )
        return [
            {
                "user_id": r.user_id,
                "message_count": r.message_count,
                "last_message_at": r.last_message_at.isoformat() if r.last_message_at else None,
            }
            for r in rows
        ]
    finally:
        session.close()


@router.get("/stats", response_model=ConversationStatsResponse)
async def conversation_stats(
    current_user: UserModel = Depends(require_hr),
):
    """Aggregated conversation statistics."""
    session = get_db_session()
    try:
        convs = session.query(ConversationModel).all()
        users = set()
        by_intent: dict[str, int] = {}
        by_agent: dict[str, int] = {}
        for c in convs:
            users.add(c.user_id)
            intent = c.intent or "unknown"
            agent = c.agent_used or "unknown"
            by_intent[intent] = by_intent.get(intent, 0) + 1
            by_agent[agent] = by_agent.get(agent, 0) + 1

        return ConversationStatsResponse(
            total_messages=len(convs),
            unique_users=len(users),
            by_intent=by_intent,
            by_agent=by_agent,
        )
    finally:
        session.close()


@router.get("/{user_id}", response_model=list[ConversationResponse])
async def get_user_conversations(
    user_id: str,
    current_user: UserModel = Depends(require_hr),
):
    """Get full chat history for a specific user."""
    session = get_db_session()
    try:
        convs = (
            session.query(ConversationModel)
            .filter_by(user_id=user_id)
            .order_by(ConversationModel.timestamp.asc())
            .all()
        )
        return [ConversationResponse(**_conv_to_dict(c)) for c in convs]
    finally:
        session.close()
