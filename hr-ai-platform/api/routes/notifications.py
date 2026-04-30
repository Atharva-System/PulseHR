"""Notifications API — persistent in-app notifications from app_notifications table."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth import require_hr
from db.connection import get_db_session
from db.models import AppNotificationModel, UserModel
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NotificationItem(BaseModel):
    id: str
    type: str          # "new_ticket" | "status_change" | "high_severity" | "escalation"
    title: str
    message: str
    severity: Optional[str] = None
    ticket_id: Optional[str] = None
    timestamp: str
    is_read: bool = False


class NotificationsResponse(BaseModel):
    total: int
    unread: int
    notifications: list[NotificationItem]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=NotificationsResponse)
async def get_notifications(
    current_user: UserModel = Depends(require_hr),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Returns the latest in-app notifications for the current HR/Authority user,
    read from the app_notifications table.
    """
    session = get_db_session()
    try:
        rows = (
            session.query(AppNotificationModel)
            .filter(AppNotificationModel.user_id == current_user.id)
            .order_by(AppNotificationModel.created_at.desc())
            .limit(limit)
            .all()
        )

        notifications = [
            NotificationItem(
                id=str(r.id),
                type=r.type,
                title=r.title,
                message=r.message or "",
                severity=r.severity,
                ticket_id=r.ticket_id,
                timestamp=r.created_at.isoformat() if r.created_at else "",
                is_read=r.is_read,
            )
            for r in rows
        ]

        unread = sum(1 for n in notifications if not n.is_read)

        return NotificationsResponse(
            total=len(notifications),
            unread=unread,
            notifications=notifications,
        )
    finally:
        session.close()


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: UserModel = Depends(require_hr),
):
    """Mark a single notification as read."""
    session = get_db_session()
    try:
        row = (
            session.query(AppNotificationModel)
            .filter(
                AppNotificationModel.id == notification_id,
                AppNotificationModel.user_id == current_user.id,
            )
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Notification not found")
        row.is_read = True
        session.commit()
        return {"status": "ok"}
    finally:
        session.close()


@router.patch("/read-all")
async def mark_all_notifications_read(
    current_user: UserModel = Depends(require_hr),
):
    """Mark all notifications for this user as read."""
    session = get_db_session()
    try:
        session.query(AppNotificationModel).filter(
            AppNotificationModel.user_id == current_user.id,
            AppNotificationModel.is_read == False,  # noqa: E712
        ).update({"is_read": True})
        session.commit()
        return {"status": "ok"}
    finally:
        session.close()


@router.delete("/clear-all")
async def clear_all_notifications(
    current_user: UserModel = Depends(require_hr),
):
    """Delete all notifications for this user."""
    session = get_db_session()
    try:
        session.query(AppNotificationModel).filter(
            AppNotificationModel.user_id == current_user.id,
        ).delete()
        session.commit()
        return {"status": "ok"}
    finally:
        session.close()
