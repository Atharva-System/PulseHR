"""Internal messaging between HR staff and Higher Authority."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import require_hr, get_current_user
from app.config import settings
from db.connection import get_db_session
from db.models import MessageModel, UserModel, AppNotificationModel
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/messages", tags=["messages"])


# ── Schemas ───────────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    recipient_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: str
    sender_id: str
    sender_username: str
    sender_role: str
    recipient_id: str
    recipient_username: str
    recipient_role: str
    content: str
    is_read: bool
    created_at: str | None


def _to_dict(m: MessageModel) -> dict:
    return {
        "id": m.id,
        "sender_id": m.sender_id,
        "sender_username": m.sender_username,
        "sender_role": m.sender_role,
        "recipient_id": m.recipient_id,
        "recipient_username": m.recipient_username,
        "recipient_role": m.recipient_role,
        "content": m.content,
        "is_read": m.is_read,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def send_message(
    body: SendMessageRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(require_hr),
):
    """Send an internal message to another HR or authority user."""
    session = get_db_session()
    try:
        # Verify recipient exists and has HR/authority role
        recipient = (
            session.query(UserModel)
            .filter(
                UserModel.id == body.recipient_id,
                UserModel.is_active == True,
                UserModel.role.in_(["hr", "higher_authority"]),
            )
            .first()
        )
        if not recipient:
            raise HTTPException(404, "Recipient not found or not an HR/authority user")

        if recipient.id == current_user.id:
            raise HTTPException(400, "Cannot send a message to yourself")

        msg = MessageModel(
            id=str(uuid.uuid4()),
            sender_id=current_user.id,
            sender_username=current_user.username,
            sender_role=current_user.role,
            recipient_id=recipient.id,
            recipient_username=recipient.username,
            recipient_role=recipient.role,
            content=body.content,
            is_read=False,
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)

        # In-app notification to recipient
        notif = AppNotificationModel(
            id=str(uuid.uuid4()),
            user_id=recipient.id,
            type="new_message",
            title=f"New message from {current_user.username}",
            message=body.content[:100] + ("..." if len(body.content) > 100 else ""),
            severity="low"
        )
        session.add(notif)
        session.commit()

        logger.info(
            f"Message sent: {current_user.username} → {recipient.username} (id={msg.id})"
        )
        return _to_dict(msg)
    finally:
        session.close()


@router.get("")
async def list_messages(
    with_user: str | None = Query(None, description="Filter conversation with specific user ID"),
    current_user: UserModel = Depends(require_hr),
):
    """Get all messages for the current user (sent + received).

    Optionally filter to a conversation with a specific user (`with_user`).
    """
    session = get_db_session()
    try:
        q = session.query(MessageModel).filter(
            (MessageModel.sender_id == current_user.id)
            | (MessageModel.recipient_id == current_user.id)
        )
        if with_user:
            q = q.filter(
                (
                    (MessageModel.sender_id == current_user.id)
                    & (MessageModel.recipient_id == with_user)
                )
                | (
                    (MessageModel.sender_id == with_user)
                    & (MessageModel.recipient_id == current_user.id)
                )
            )
        rows = q.order_by(MessageModel.created_at.asc()).all()
        return [_to_dict(r) for r in rows]
    finally:
        session.close()


@router.get("/unread-count")
async def unread_count(
    current_user: UserModel = Depends(require_hr),
):
    """Return count of unread messages for the current user."""
    session = get_db_session()
    try:
        count = (
            session.query(MessageModel)
            .filter(
                MessageModel.recipient_id == current_user.id,
                MessageModel.is_read == False,
            )
            .count()
        )
        return {"unread": count}
    finally:
        session.close()


@router.get("/conversations")
async def list_conversations(
    current_user: UserModel = Depends(require_hr),
):
    """Return a list of unique users the current user has exchanged messages with,
    with the latest message and unread count for each thread.
    """
    session = get_db_session()
    try:
        all_msgs = (
            session.query(MessageModel)
            .filter(
                (MessageModel.sender_id == current_user.id)
                | (MessageModel.recipient_id == current_user.id)
            )
            .order_by(MessageModel.created_at.desc())
            .all()
        )

        # Build per-user thread summary
        threads: dict[str, dict] = {}
        for m in all_msgs:
            other_id = m.recipient_id if m.sender_id == current_user.id else m.sender_id
            other_username = m.recipient_username if m.sender_id == current_user.id else m.sender_username
            other_role = m.recipient_role if m.sender_id == current_user.id else m.sender_role
            if other_id not in threads:
                threads[other_id] = {
                    "user_id": other_id,
                    "username": other_username,
                    "role": other_role,
                    "last_message": m.content,
                    "last_at": m.created_at.isoformat() if m.created_at else None,
                    "unread": 0,
                }
            if m.recipient_id == current_user.id and not m.is_read:
                threads[other_id]["unread"] += 1

        return list(threads.values())
    finally:
        session.close()


@router.patch("/{message_id}/read")
async def mark_read(
    message_id: str,
    current_user: UserModel = Depends(require_hr),
):
    """Mark a single message as read."""
    session = get_db_session()
    try:
        msg = (
            session.query(MessageModel)
            .filter(
                MessageModel.id == message_id,
                MessageModel.recipient_id == current_user.id,
            )
            .first()
        )
        if not msg:
            raise HTTPException(404, "Message not found")
        msg.is_read = True
        session.commit()
        return {"ok": True}
    finally:
        session.close()


@router.patch("/read-all")
async def mark_all_read(
    with_user: str | None = Query(None),
    current_user: UserModel = Depends(require_hr),
):
    """Mark all messages from a specific sender (or all) as read."""
    session = get_db_session()
    try:
        q = session.query(MessageModel).filter(
            MessageModel.recipient_id == current_user.id,
            MessageModel.is_read == False,
        )
        if with_user:
            q = q.filter(MessageModel.sender_id == with_user)
        rows = q.all()
        for m in rows:
            m.is_read = True
        session.commit()
        return {"marked_read": len(rows)}
    finally:
        session.close()
