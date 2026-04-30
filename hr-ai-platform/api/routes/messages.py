"""Internal messaging between HR staff and Higher Authority."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth import require_hr, get_current_user
from app.config import settings
from db.connection import get_db_session
from db.models import MessageModel, UserModel
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

        # Email notification to recipient
        try:
            if recipient.email:
                from skills.communication.email import send_email
                role_label = "Higher Authority" if current_user.role == "higher_authority" else "HR"
                sender_name = current_user.full_name or current_user.username
                sent_at = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
                html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Roboto,Arial,sans-serif;background:#f1f5f9;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <tr>
          <td style="background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:28px 32px;">
            <span style="font-size:22px;font-weight:700;color:#ffffff;">📩 New Internal Message</span><br/>
            <span style="font-size:13px;color:rgba(255,255,255,0.8);">Pulsee AI — Internal Messaging</span>
          </td>
        </tr>
        <tr>
          <td style="padding:32px;">
            <p style="margin:0 0 4px;font-size:13px;color:#64748b;">From</p>
            <p style="margin:0 0 16px;font-size:16px;font-weight:600;color:#1e293b;">{sender_name} <span style="font-size:12px;color:#7c3aed;background:#ede9fe;padding:2px 8px;border-radius:12px;">{role_label}</span></p>
            <p style="margin:0 0 4px;font-size:13px;color:#64748b;">Sent at</p>
            <p style="margin:0 0 24px;font-size:14px;color:#1e293b;">{sent_at}</p>
            <p style="margin:0 0 8px;font-size:13px;color:#64748b;text-transform:uppercase;letter-spacing:1px;font-weight:600;">Message</p>
            <div style="background:#f8fafc;border-left:4px solid #4f46e5;border-radius:0 8px 8px 0;padding:16px 20px;">
              <p style="margin:0;font-size:15px;color:#1e293b;line-height:1.6;white-space:pre-wrap;">{body.content}</p>
            </div>
            <br/>
            <p style="text-align:center;">
                            <a href="{settings.frontend_url.rstrip('/')}/#/{('admin' if current_user.role == 'higher_authority' else 'hr')}/messages" style="display:inline-block;background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#ffffff;font-size:14px;font-weight:600;padding:12px 32px;border-radius:8px;text-decoration:none;">Open in Pulsee →</a>
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:16px 32px;">
            <p style="margin:0;font-size:12px;color:#94a3b8;text-align:center;">This is an automated notification from <strong>Pulsee AI</strong>.</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
                send_email(
                    to=recipient.email,
                    subject=f"[Pulsee] New message from {current_user.username}",
                    body=html_body,
                    html=True,
                )
        except Exception as e:
            logger.warning(f"Could not send email notification for message: {e}")

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
