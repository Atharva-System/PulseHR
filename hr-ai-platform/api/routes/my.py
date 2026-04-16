"""User-facing API routes — own chat history and ticket status."""

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import get_current_user
from db.connection import get_db_session
from db.models import ConversationModel, TicketModel, UserModel
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/my", tags=["my"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MyConversationResponse(BaseModel):
    entry_id: str
    message: str
    response: str
    intent: str
    agent_used: str
    timestamp: Optional[str] = None


class MyTicketResponse(BaseModel):
    ticket_id: str
    title: str
    description: str
    severity: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/conversations", response_model=list[MyConversationResponse])
async def my_conversations(
    days: int = Query(30, ge=1, le=365),
    current_user: UserModel = Depends(get_current_user),
):
    """Get the current user's chat history for the last N days (default 30)."""
    session = get_db_session()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        convs = (
            session.query(ConversationModel)
            .filter(
                ConversationModel.user_id == current_user.username,
                ConversationModel.timestamp >= cutoff,
            )
            .order_by(ConversationModel.timestamp.asc())
            .all()
        )
        return [
            MyConversationResponse(
                entry_id=c.entry_id,
                message=c.message or "",
                response=c.response or "",
                intent=c.intent or "",
                agent_used=c.agent_used or "",
                timestamp=c.timestamp.isoformat() if c.timestamp else None,
            )
            for c in convs
        ]
    finally:
        session.close()


@router.get("/tickets", response_model=list[MyTicketResponse])
async def my_tickets(
    current_user: UserModel = Depends(get_current_user),
):
    """Get tickets belonging to the current user."""
    session = get_db_session()
    try:
        tickets = (
            session.query(TicketModel)
            .filter(TicketModel.user_id == current_user.username)
            .order_by(TicketModel.created_at.desc())
            .all()
        )
        return [
            MyTicketResponse(
                ticket_id=t.ticket_id,
                title=t.title or "",
                description=t.description or "",
                severity=t.severity or "",
                status=t.status or "",
                created_at=t.created_at.isoformat() if t.created_at else None,
                updated_at=t.updated_at.isoformat() if t.updated_at else None,
            )
            for t in tickets
        ]
    finally:
        session.close()
