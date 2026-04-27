"""Admin API routes — ticket management for HR / Higher Authority."""

from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth import require_hr
from db.connection import get_db_session
from db.models import TicketModel, ConversationModel, AuditLogModel, UserModel, TicketCommentModel
from escalation.notifier import _build_html_email
from skills.communication.email import send_email
from utils.helpers import generate_id
from utils.logger import get_logger
from utils.privacy import redact_reporter_label, can_view_chat_content

logger = get_logger(__name__)

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


# ---------------------------------------------------------------------------
# SLA config (hours by severity)
# ---------------------------------------------------------------------------

SLA_HOURS = {
    "critical": 1,
    "high": 4,
    "medium": 24,
    "low": 72,
}


def compute_sla_deadline(severity: str, created_at: datetime) -> datetime:
    """Compute SLA deadline based on severity."""
    hours = SLA_HOURS.get(severity, 72)
    return created_at + timedelta(hours=hours)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TicketResponse(BaseModel):
    ticket_id: str
    title: str
    description: str
    severity: str
    privacy_mode: str
    complaint_target: str = ""
    assignee: str
    assignee_id: Optional[str] = None
    status: str
    user_id: str
    trace_id: str
    sla_deadline: Optional[str] = None
    sla_breached: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TicketDetailResponse(TicketResponse):
    conversations: list[dict] = []
    audit_trail: list[dict] = []
    comments: list[dict] = []


class UpdateTicketStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(open|in_progress|resolved|closed)$")


class AssignTicketRequest(BaseModel):
    assignee_id: str
    assignee_name: str = ""


class AddCommentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    is_internal: bool = True


class TicketStatsResponse(BaseModel):
    total: int
    by_status: dict
    by_severity: dict
    sla_breached: int
    avg_resolution_hours: Optional[float] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ticket_to_dict(t: TicketModel, viewer_role: str) -> dict:
    now = datetime.now(timezone.utc)
    sla_breached = t.sla_breached or False
    if t.sla_deadline and t.status in ("open", "in_progress") and now > t.sla_deadline:
        sla_breached = True

    privacy_mode = t.privacy_mode or "identified"
    return {
        "ticket_id": t.ticket_id,
        "title": t.title,
        "description": t.description or "",
        "severity": t.severity or "",
        "privacy_mode": privacy_mode,
        "complaint_target": getattr(t, "complaint_target", "") or "",
        "assignee": t.assignee or "",
        "assignee_id": t.assignee_id or None,
        "status": t.status or "",
        "user_id": redact_reporter_label(t.user_id or "", privacy_mode, viewer_role),
        "trace_id": t.trace_id or "",
        "sla_deadline": t.sla_deadline.isoformat() if t.sla_deadline else None,
        "sla_breached": sla_breached,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def _allowed_ticket_levels(current_user: UserModel) -> set[str] | None:
    """Return visible severity levels for the current viewer.

    - higher_authority: unrestricted
    - hr: restricted to assigned notification levels
    """
    if current_user.role == "higher_authority":
        return None

    if not current_user.receive_notifications:
        return set()

    return {
        (level or "").strip().lower()
        for level in (current_user.notification_levels or "").split(",")
        if (level or "").strip()
    }


def _can_view_ticket_by_level(ticket: TicketModel, current_user: UserModel) -> bool:
    allowed_levels = _allowed_ticket_levels(current_user)
    if allowed_levels is None:
        return True
    return (ticket.severity or "").lower() in allowed_levels


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[TicketResponse])
async def list_tickets(
    ticket_status: Optional[str] = Query(None, alias="status", pattern="^(open|in_progress|resolved|closed)$"),
    severity: Optional[str] = Query(None, pattern="^(low|medium|high|critical)$"),
    user_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="ISO date, e.g. 2026-01-01"),
    date_to: Optional[str] = Query(None, description="ISO date, e.g. 2026-12-31"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: UserModel = Depends(require_hr),
):
    """List all tickets with optional filters and pagination."""
    from utils.privacy import is_complaint_about_hr

    session = get_db_session()
    try:
        allowed_levels = _allowed_ticket_levels(current_user)
        q = session.query(TicketModel)
        if ticket_status:
            q = q.filter(TicketModel.status == ticket_status)
        if severity:
            q = q.filter(TicketModel.severity == severity)
        if user_id:
            q = q.filter(TicketModel.user_id == user_id)
        if date_from:
            q = q.filter(TicketModel.created_at >= datetime.fromisoformat(date_from))
        if date_to:
            q = q.filter(TicketModel.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))
        if allowed_levels is not None:
            if not allowed_levels:
                return []
            q = q.filter(TicketModel.severity.in_(sorted(allowed_levels)))

        total = q.count()
        tickets = (
            q.order_by(TicketModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # --- Hide tickets about HR staff from HR viewers ---
        # Only higher_authority (admin) can see complaints targeting HR people
        result = []
        for t in tickets:
            target = getattr(t, "complaint_target", "") or ""
            if current_user.role == "hr" and target and is_complaint_about_hr(target):
                logger.info(
                    f"Hiding ticket {t.ticket_id} from HR viewer — "
                    f"complaint targets HR staff: {target}"
                )
                continue
            result.append(TicketResponse(**_ticket_to_dict(t, current_user.role)))
        return result
    finally:
        session.close()


@router.get("/stats", response_model=TicketStatsResponse)
async def ticket_stats(
    current_user: UserModel = Depends(require_hr),
):
    """Aggregated ticket statistics."""
    session = get_db_session()
    try:
        allowed_levels = _allowed_ticket_levels(current_user)
        q = session.query(TicketModel)
        if allowed_levels is not None:
            if not allowed_levels:
                return TicketStatsResponse(
                    total=0,
                    by_status={},
                    by_severity={},
                    sla_breached=0,
                    avg_resolution_hours=None,
                )
            q = q.filter(TicketModel.severity.in_(sorted(allowed_levels)))
        tickets = q.all()
        now = datetime.now(timezone.utc)
        by_status: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        breached = 0
        resolution_times: list[float] = []
        for t in tickets:
            s = t.status or "unknown"
            sev = t.severity or "unknown"
            by_status[s] = by_status.get(s, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1
            # SLA breach check
            if t.sla_deadline and t.status in ("open", "in_progress") and now > t.sla_deadline:
                breached += 1
            if t.sla_breached:
                breached += 1
            # Resolution time
            if t.status in ("resolved", "closed") and t.created_at and t.updated_at:
                hours = (t.updated_at - t.created_at).total_seconds() / 3600
                resolution_times.append(hours)

        avg_resolution = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else None

        return TicketStatsResponse(
            total=len(tickets),
            by_status=by_status,
            by_severity=by_severity,
            sla_breached=breached,
            avg_resolution_hours=avg_resolution,
        )
    finally:
        session.close()


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: str,
    current_user: UserModel = Depends(require_hr),
):
    """Get a single ticket with related conversations, audit trail, and comments."""
    from utils.privacy import is_complaint_about_hr

    session = get_db_session()
    try:
        ticket = session.query(TicketModel).filter_by(ticket_id=ticket_id).first()
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if not _can_view_ticket_by_level(ticket, current_user):
            raise HTTPException(
                status_code=403,
                detail="This ticket is outside your assigned severity access levels",
            )

        # Block HR from viewing tickets that target HR staff
        target = getattr(ticket, "complaint_target", "") or ""
        if current_user.role == "hr" and target and is_complaint_about_hr(target):
            raise HTTPException(
                status_code=403,
                detail="This ticket is restricted — only higher authority can view it",
            )

        # Related conversations (by trace_id or user_id)
        convs = []
        if ticket.trace_id:
            conv_rows = (
                session.query(ConversationModel)
                .filter_by(trace_id=ticket.trace_id)
                .order_by(ConversationModel.timestamp.asc())
                .all()
            )
            convs = [
                {
                    "entry_id": c.entry_id,
                    "user_id": redact_reporter_label(
                        c.user_id,
                        ticket.privacy_mode or "identified",
                        current_user.role,
                    ),
                    "message": (
                        c.message
                        if can_view_chat_content(ticket.privacy_mode or "identified", current_user.role)
                        else "[Content hidden — privacy protected]"
                    ),
                    "response": (
                        c.response
                        if can_view_chat_content(ticket.privacy_mode or "identified", current_user.role)
                        else "[Content hidden — privacy protected]"
                    ),
                    "intent": c.intent,
                    "agent_used": c.agent_used,
                    "timestamp": c.timestamp.isoformat() if c.timestamp else None,
                }
                for c in conv_rows
            ]

        # Audit trail
        audit = []
        if ticket.trace_id:
            audit_rows = (
                session.query(AuditLogModel)
                .filter_by(trace_id=ticket.trace_id)
                .order_by(AuditLogModel.timestamp.desc())
                .all()
            )
            audit = [
                {
                    "id": a.id,
                    "event_type": a.event_type,
                    "details": a.details,
                    "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                }
                for a in audit_rows
            ]

        # Comments
        comment_rows = (
            session.query(TicketCommentModel)
            .filter_by(ticket_id=ticket_id)
            .order_by(TicketCommentModel.created_at.asc())
            .all()
        )
        comments = [
            {
                "id": c.id,
                "user_id": c.user_id,
                "username": c.username or "",
                "content": c.content,
                "is_internal": c.is_internal,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in comment_rows
        ]

        data = _ticket_to_dict(ticket, current_user.role)
        data["conversations"] = convs
        data["audit_trail"] = audit
        data["comments"] = comments
        return TicketDetailResponse(**data)
    finally:
        session.close()


@router.patch("/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: str,
    body: UpdateTicketStatusRequest,
    current_user: UserModel = Depends(require_hr),
):
    """Update ticket status. HR and Higher Authority only."""
    session = get_db_session()
    try:
        ticket = session.query(TicketModel).filter_by(ticket_id=ticket_id).first()
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if not _can_view_ticket_by_level(ticket, current_user):
            raise HTTPException(
                status_code=403,
                detail="This ticket is outside your assigned severity access levels",
            )

        old_status = ticket.status
        ticket.status = body.status
        session.commit()

        logger.info(
            f"Ticket {ticket_id} status changed: {old_status} -> {body.status} "
            f"by {current_user.username}"
        )
        return {
            "ticket_id": ticket_id,
            "old_status": old_status,
            "new_status": body.status,
            "updated_by": current_user.username,
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Ticket Comments
# ---------------------------------------------------------------------------

@router.post("/{ticket_id}/comments")
async def add_comment(
    ticket_id: str,
    body: AddCommentRequest,
    current_user: UserModel = Depends(require_hr),
):
    """Add an internal note or comment to a ticket."""
    session = get_db_session()
    try:
        ticket = session.query(TicketModel).filter_by(ticket_id=ticket_id).first()
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if not _can_view_ticket_by_level(ticket, current_user):
            raise HTTPException(
                status_code=403,
                detail="This ticket is outside your assigned severity access levels",
            )

        comment = TicketCommentModel(
            id=generate_id("CMT"),
            ticket_id=ticket_id,
            user_id=current_user.id,
            username=current_user.username,
            content=body.content,
            is_internal=body.is_internal,
        )
        session.add(comment)
        session.commit()

        logger.info(f"Comment added to ticket {ticket_id} by {current_user.username}")
        return {
            "id": comment.id,
            "ticket_id": ticket_id,
            "username": current_user.username,
            "content": body.content,
            "is_internal": body.is_internal,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
        }
    finally:
        session.close()


@router.get("/{ticket_id}/comments")
async def list_comments(
    ticket_id: str,
    current_user: UserModel = Depends(require_hr),
):
    """List all comments on a ticket."""
    session = get_db_session()
    try:
        ticket = session.query(TicketModel).filter_by(ticket_id=ticket_id).first()
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if not _can_view_ticket_by_level(ticket, current_user):
            raise HTTPException(
                status_code=403,
                detail="This ticket is outside your assigned severity access levels",
            )
        comments = (
            session.query(TicketCommentModel)
            .filter_by(ticket_id=ticket_id)
            .order_by(TicketCommentModel.created_at.asc())
            .all()
        )
        return [
            {
                "id": c.id,
                "user_id": c.user_id,
                "username": c.username or "",
                "content": c.content,
                "is_internal": c.is_internal,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in comments
        ]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Ticket Assignment
# ---------------------------------------------------------------------------

@router.patch("/{ticket_id}/assign")
async def assign_ticket(
    ticket_id: str,
    body: AssignTicketRequest,
    current_user: UserModel = Depends(require_hr),
):
    """Assign a ticket to a specific HR staff member."""
    session = get_db_session()
    try:
        ticket = session.query(TicketModel).filter_by(ticket_id=ticket_id).first()
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if not _can_view_ticket_by_level(ticket, current_user):
            raise HTTPException(
                status_code=403,
                detail="This ticket is outside your assigned severity access levels",
            )
        if (ticket.status or "").lower() == "closed":
            raise HTTPException(
                status_code=400,
                detail="Closed tickets cannot be reassigned",
            )

        # Verify assignee exists and is HR or higher_authority
        assignee = session.query(UserModel).filter_by(id=body.assignee_id, is_active=True).first()
        if assignee is None:
            raise HTTPException(status_code=404, detail="Assignee user not found")
        if assignee.role not in ("hr", "higher_authority"):
            raise HTTPException(status_code=400, detail="Can only assign to HR staff")
        if assignee.id == current_user.id:
            raise HTTPException(
                status_code=400,
                detail="You cannot assign the ticket to yourself",
            )
        if current_user.role == "hr":
            assignee_levels = {
                (level or "").strip().lower()
                for level in (assignee.notification_levels or "").split(",")
                if (level or "").strip()
            }
            if (ticket.severity or "").lower() not in assignee_levels:
                raise HTTPException(
                    status_code=400,
                    detail="Selected assignee is not assigned to this ticket severity level",
                )

        old_assignee = ticket.assignee
        ticket.assignee = assignee.full_name or assignee.username
        ticket.assignee_id = assignee.id
        session.commit()

        # Send email notification to the assigned person
        try:
            reporter_label = redact_reporter_label(
                ticket.user_id or "",
                ticket.privacy_mode or "identified",
                assignee.role,
            )
            assignment_summary = (
                f"You have been assigned a new ticket.\n\n"
                f"Ticket ID: {ticket.ticket_id}\n"
                f"Title: {ticket.title}\n"
                f"Severity: {ticket.severity}\n"
                f"Status: {ticket.status}\n"
                f"Privacy Mode: {ticket.privacy_mode or 'identified'}\n"
                f"Reported by: {reporter_label}\n"
                f"Assigned by: {current_user.full_name or current_user.username}"
            )
            email_body = _build_html_email(assignment_summary, ticket.severity)
            send_email(
                to=assignee.email,
                subject=f"📋 Ticket Assigned to You — {ticket.ticket_id} ({ticket.severity.upper()})",
                body=email_body,
                html=True,
            )
            logger.info(f"Assignment notification sent to {assignee.email}")
        except Exception as e:
            logger.error(f"Failed to send assignment email to {assignee.email}: {e}")

        logger.info(
            f"Ticket {ticket_id} assigned: {old_assignee} -> {ticket.assignee} "
            f"by {current_user.username}"
        )
        return {
            "ticket_id": ticket_id,
            "old_assignee": old_assignee,
            "new_assignee": ticket.assignee,
            "assignee_id": assignee.id,
            "assigned_by": current_user.username,
        }
    finally:
        session.close()


# ---------------------------------------------------------------------------
# SLA Check
# ---------------------------------------------------------------------------

@router.get("/sla/breached")
async def sla_breached_tickets(
    current_user: UserModel = Depends(require_hr),
):
    """List tickets that have breached their SLA deadline."""
    session = get_db_session()
    try:
        now = datetime.now(timezone.utc)
        allowed_levels = _allowed_ticket_levels(current_user)
        q = session.query(TicketModel).filter(
            TicketModel.status.in_(["open", "in_progress"]),
            TicketModel.sla_deadline.isnot(None),
            TicketModel.sla_deadline < now,
        )
        if allowed_levels is not None:
            if not allowed_levels:
                return []
            q = q.filter(TicketModel.severity.in_(sorted(allowed_levels)))
        tickets = q.order_by(TicketModel.sla_deadline.asc()).all()
        return [_ticket_to_dict(t, current_user.role) for t in tickets]
    finally:
        session.close()
