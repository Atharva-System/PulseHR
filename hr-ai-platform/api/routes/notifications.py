"""Notifications API — new tickets/events since the user's last login."""

from typing import Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func

from app.auth import require_hr
from db.connection import get_db_session
from db.models import TicketModel, AuditLogModel, UserModel
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NotificationItem(BaseModel):
    id: str
    type: str          # "new_ticket" | "status_change" | "high_severity"
    title: str
    message: str
    severity: Optional[str] = None
    ticket_id: Optional[str] = None
    timestamp: str
    is_read: bool = False


class NotificationsResponse(BaseModel):
    total: int
    unread: int
    since: Optional[str] = None
    notifications: list[NotificationItem]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _severity_label(sev: str) -> str:
    return {"critical": "🔴 Critical", "high": "🟠 High", "medium": "🟡 Medium", "low": "🟢 Low"}.get(sev, sev)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=NotificationsResponse)
async def get_notifications(
    current_user: UserModel = Depends(require_hr),
):
    """
    Returns notifications for HR/Authority users.
    Shows new tickets and status changes since the user's *previous* login.
    If no previous login, shows the last 24 hours.
    """
    # Use previous_login (the login before the current session) so the user
    # sees everything that happened while they were away.
    since = current_user.previous_login
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(hours=24)

    session = get_db_session()
    try:
        notifications: list[NotificationItem] = []

        # ── 1. New tickets created since last login ──────────────────────
        new_tickets = (
            session.query(TicketModel)
            .filter(TicketModel.created_at >= since)
            .order_by(TicketModel.created_at.desc())
            .all()
        )
        for t in new_tickets:
            is_urgent = t.severity in ("high", "critical")
            notifications.append(NotificationItem(
                id=f"nt-{t.ticket_id}",
                type="high_severity" if is_urgent else "new_ticket",
                title=f"{'⚠️ Urgent: ' if is_urgent else ''}New Ticket — {t.title}",
                message=f"{_severity_label(t.severity)} complaint from {t.user_id}",
                severity=t.severity,
                ticket_id=t.ticket_id,
                timestamp=t.created_at.isoformat() if t.created_at else "",
            ))

        # ── 2. Status changes (audit log) since last login ──────────────
        status_events = (
            session.query(AuditLogModel)
            .filter(
                AuditLogModel.timestamp >= since,
                AuditLogModel.event_type.in_(["status_changed", "ticket_resolved", "ticket_closed"]),
            )
            .order_by(AuditLogModel.timestamp.desc())
            .all()
        )
        for a in status_events:
            notifications.append(NotificationItem(
                id=f"na-{a.id}",
                type="status_change",
                title="Ticket Status Updated",
                message=a.details or "A ticket status was changed",
                ticket_id=a.trace_id,
                timestamp=a.timestamp.isoformat() if a.timestamp else "",
            ))

        # Sort all notifications by timestamp descending
        notifications.sort(key=lambda n: n.timestamp, reverse=True)

        return NotificationsResponse(
            total=len(notifications),
            unread=len(notifications),  # all are "unread" since last login
            since=since.isoformat(),
            notifications=notifications,
        )
    finally:
        session.close()
