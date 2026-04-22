"""Conversation API routes — view chat history for HR / Higher Authority."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import require_hr
from db.connection import get_db_session
from db.models import ConversationModel, UserModel
from utils.logger import get_logger
from utils.privacy import redact_reporter_label, can_view_chat_content, can_view_user_in_list

logger = get_logger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ConversationResponse(BaseModel):
    entry_id: str
    user_id: str
    privacy_mode: str
    message: str
    response: str
    intent: str
    emotion: str
    severity: str
    agent_used: str
    trace_id: str
    timestamp: Optional[str] = None


class ConversationUserResponse(BaseModel):
    user_id: str
    lookup_user_id: Optional[str] = None
    privacy_mode: str = "identified"
    message_count: int
    last_message_at: Optional[str] = None


class ConversationStatsResponse(BaseModel):
    total_messages: int
    unique_users: int
    by_intent: dict
    by_agent: dict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _privacy_rank(mode: str) -> int:
    order = {"identified": 0, "confidential": 1, "anonymous": 2}
    return order.get(mode or "identified", 0)


def _conv_to_dict(c: ConversationModel, viewer_role: str) -> dict:
    privacy_mode = c.privacy_mode or "identified"
    viewable = can_view_chat_content(privacy_mode, viewer_role)
    return {
        "entry_id": c.entry_id,
        "user_id": redact_reporter_label(c.user_id or "", privacy_mode, viewer_role),
        "privacy_mode": privacy_mode,
        "message": (c.message or "") if viewable else "[Content hidden — privacy protected]",
        "response": (c.response or "") if viewable else "[Content hidden — privacy protected]",
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

        # anonymous and confidential chats are invisible to HR in the list endpoint
        if current_user.role != "higher_authority":
            q = q.filter(ConversationModel.privacy_mode == "identified")
        else:
            q = q.filter(ConversationModel.privacy_mode != "anonymous")

        conversations = (
            q.order_by(ConversationModel.timestamp.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [ConversationResponse(**_conv_to_dict(c, current_user.role)) for c in conversations]
    finally:
        session.close()


@router.get("/users", response_model=list[ConversationUserResponse])
async def list_conversation_users(
    current_user: UserModel = Depends(require_hr),
):
    """List all users who have conversations, with their message counts."""
    session = get_db_session()
    try:
        rows = (
            session.query(ConversationModel)
            .order_by(ConversationModel.timestamp.desc())
            .all()
        )

        grouped: dict[str, dict] = {}
        for row in rows:
            user_key = row.user_id or ""
            privacy_mode = row.privacy_mode or "identified"
            item = grouped.get(user_key)
            if item is None:
                grouped[user_key] = {
                    "actual_user_id": user_key,
                    "privacy_mode": privacy_mode,
                    "message_count": 1,
                    "last_message_at": row.timestamp,
                }
                continue

            item["message_count"] += 1
            if row.timestamp and (
                item["last_message_at"] is None or row.timestamp > item["last_message_at"]
            ):
                item["last_message_at"] = row.timestamp
            if _privacy_rank(privacy_mode) > _privacy_rank(item["privacy_mode"]):
                item["privacy_mode"] = privacy_mode

        ordered = sorted(
            grouped.values(),
            key=lambda item: item["last_message_at"] or 0,
            reverse=True,
        )

        # Filter: only show users the current viewer is allowed to see
        role = current_user.role
        visible = [item for item in ordered if can_view_user_in_list(item["privacy_mode"], role)]

        return [
            ConversationUserResponse(
                user_id=redact_reporter_label(
                    item["actual_user_id"],
                    item["privacy_mode"],
                    role,
                ),
                # HR can always click to see identified-mode messages for this user;
                # anonymous users have no lookup_user_id (already filtered out for HR)
                lookup_user_id=(
                    item["actual_user_id"]
                    if item["privacy_mode"] != "anonymous" or role == "higher_authority"
                    else None
                ),
                privacy_mode=item["privacy_mode"],
                message_count=item["message_count"],
                last_message_at=(
                    item["last_message_at"].isoformat()
                    if item["last_message_at"]
                    else None
                ),
            )
            for item in visible
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
        q = session.query(ConversationModel)
        # HR only sees identified; admin sees identified + confidential
        if current_user.role != "higher_authority":
            q = q.filter(ConversationModel.privacy_mode == "identified")
        else:
            q = q.filter(ConversationModel.privacy_mode != "anonymous")
        convs = q.all()
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

        role = current_user.role
        result = []
        for c in convs:
            pm = c.privacy_mode or "identified"

            # anonymous → invisible to everyone
            if pm == "anonymous":
                continue

            # confidential → only admin can see; HR skips these messages
            if pm == "confidential" and role != "higher_authority":
                continue

            # identified → everyone can see
            result.append(ConversationResponse(**_conv_to_dict(c, role)))

        return result
    finally:
        session.close()
