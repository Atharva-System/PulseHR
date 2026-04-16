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

def _ticket_to_dict(t: TicketModel) -> dict:
    now = datetime.now(timezone.utc)
    sla_breached = t.sla_breached or False
    if t.sla_deadline and t.status in ("open", "in_progress") and now > t.sla_deadline:
        sla_breached = True
    return {
        "ticket_id": t.ticket_id,
        "title": t.title,
        "description": t.description or "",
        "severity": t.severity or "",
        "assignee": t.assignee or "",
        "assignee_id": t.assignee_id or None,
        "status": t.status or "",
        "user_id": t.user_id or "",
        "trace_id": t.trace_id or "",
        "sla_deadline": t.sla_deadline.isoformat() if t.sla_deadline else None,
        "sla_breached": sla_breached,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


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
    session = get_db_session()
    try:
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

        total = q.count()
        tickets = (
            q.order_by(TicketModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [TicketResponse(**_ticket_to_dict(t)) for t in tickets]
    finally:
        session.close()


@router.get("/stats", response_model=TicketStatsResponse)
async def ticket_stats(
    current_user: UserModel = Depends(require_hr),
):
    """Aggregated ticket statistics."""
    session = get_db_session()
    try:
        tickets = session.query(TicketModel).all()
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
    session = get_db_session()
    try:
        ticket = session.query(TicketModel).filter_by(ticket_id=ticket_id).first()
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")

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
                    "user_id": c.user_id,
                    "message": c.message,
                    "response": c.response,
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

        data = _ticket_to_dict(ticket)
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

        # Verify assignee exists and is HR or higher_authority
        assignee = session.query(UserModel).filter_by(id=body.assignee_id, is_active=True).first()
        if assignee is None:
            raise HTTPException(status_code=404, detail="Assignee user not found")
        if assignee.role not in ("hr", "higher_authority"):
            raise HTTPException(status_code=400, detail="Can only assign to HR staff")

        old_assignee = ticket.assignee
        ticket.assignee = assignee.full_name or assignee.username
        ticket.assignee_id = assignee.id
        session.commit()

        # Send email notification to the assigned person
        try:
            assignment_summary = (
                f"You have been assigned a new ticket.\n\n"
                f"Ticket ID: {ticket.ticket_id}\n"
                f"Title: {ticket.title}\n"
                f"Severity: {ticket.severity}\n"
                f"Status: {ticket.status}\n"
                f"Reported by: {ticket.user_id}\n"
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
        tickets = (
            session.query(TicketModel)
            .filter(
                TicketModel.status.in_(["open", "in_progress"]),
                TicketModel.sla_deadline.isnot(None),
                TicketModel.sla_deadline < now,
            )
            .order_by(TicketModel.sla_deadline.asc())
            .all()
        )
        return [_ticket_to_dict(t) for t in tickets]
    finally:
        session.close()
