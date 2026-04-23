"""Feedback API — user ratings after ticket resolution."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import get_current_user, require_hr
from db.connection import get_db_session
from db.models import FeedbackModel, TicketModel, UserModel
from utils.helpers import generate_id
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SubmitFeedbackRequest(BaseModel):
    ticket_id: str
    rating: float = Field(..., ge=1, le=5)
    comment: str = ""


class FeedbackResponse(BaseModel):
    id: str
    ticket_id: str
    user_id: str
    rating: float
    comment: str
    created_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    body: SubmitFeedbackRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Submit feedback/rating for a resolved ticket."""
    session = get_db_session()
    try:
        # Verify ticket exists and belongs to user
        ticket = session.query(TicketModel).filter_by(ticket_id=body.ticket_id).first()
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if ticket.user_id != current_user.username:
            raise HTTPException(status_code=403, detail="Not your ticket")
        if ticket.status not in ("resolved", "closed"):
            raise HTTPException(status_code=400, detail="Ticket must be resolved or closed to leave feedback")

        # Check if already submitted
        existing = session.query(FeedbackModel).filter_by(
            ticket_id=body.ticket_id, user_id=current_user.username
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Feedback already submitted for this ticket")

        fb = FeedbackModel(
            id=generate_id("FB"),
            ticket_id=body.ticket_id,
            user_id=current_user.username,
            rating=body.rating,
            comment=body.comment,
        )
        session.add(fb)
        session.commit()

        logger.info(f"Feedback submitted: ticket={body.ticket_id} rating={body.rating} by {current_user.username}")

        # --- Bad review escalation: rating ≤ 2 → re-open ticket + notify authority ---
        if body.rating <= 2:
            try:
                ticket.status = "open"
                session.commit()
                logger.info(f"Bad review: ticket {body.ticket_id} re-opened (rating={body.rating})")

                from escalation.notifier import notify_authority
                employee_name = current_user.full_name or current_user.username
                notify_authority(
                    f"BAD REVIEW ESCALATION — Ticket {body.ticket_id}\n\n"
                    f"Employee: {employee_name}\n"
                    f"Ticket: {body.ticket_id} — {ticket.title}\n"
                    f"Rating: {body.rating}/5\n"
                    f"Comment: {body.comment or '(no comment)'}\n\n"
                    f"The ticket has been re-opened automatically. Please review.",
                    severity=ticket.severity or "high",
                    ticket_id=str(body.ticket_id),
                )
                logger.info(f"Bad review escalation email sent for ticket {body.ticket_id}")
            except Exception as esc_err:
                logger.error(f"Bad review escalation failed: {esc_err}")

        return FeedbackResponse(
            id=fb.id,
            ticket_id=fb.ticket_id,
            user_id=fb.user_id,
            rating=fb.rating,
            comment=fb.comment or "",
            created_at=fb.created_at.isoformat() if fb.created_at else None,
        )
    finally:
        session.close()


@router.get("/{ticket_id}", response_model=Optional[FeedbackResponse])
async def get_feedback(
    ticket_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    """Get feedback for a specific ticket."""
    session = get_db_session()
    try:
        fb = session.query(FeedbackModel).filter_by(ticket_id=ticket_id).first()
        if fb is None:
            return None
        return FeedbackResponse(
            id=fb.id,
            ticket_id=fb.ticket_id,
            user_id=fb.user_id,
            rating=fb.rating,
            comment=fb.comment or "",
            created_at=fb.created_at.isoformat() if fb.created_at else None,
        )
    finally:
        session.close()


@router.get("", response_model=list[FeedbackResponse])
async def list_feedback(
    current_user: UserModel = Depends(require_hr),
):
    """List all feedback — HR only."""
    session = get_db_session()
    try:
        rows = (
            session.query(FeedbackModel)
            .order_by(FeedbackModel.created_at.desc())
            .limit(200)
            .all()
        )
        return [
            FeedbackResponse(
                id=fb.id,
                ticket_id=fb.ticket_id,
                user_id=fb.user_id,
                rating=fb.rating,
                comment=fb.comment or "",
                created_at=fb.created_at.isoformat() if fb.created_at else None,
            )
            for fb in rows
        ]
    finally:
        session.close()


@router.get("/stats/summary")
async def feedback_stats(
    current_user: UserModel = Depends(require_hr),
):
    """Get feedback summary statistics."""
    session = get_db_session()
    try:
        rows = session.query(FeedbackModel).all()
        if not rows:
            return {"total": 0, "average_rating": 0, "rating_distribution": {}}

        total = len(rows)
        avg = round(sum(r.rating for r in rows) / total, 2)
        dist: dict[str, int] = {}
        for r in rows:
            key = str(int(r.rating))
            dist[key] = dist.get(key, 0) + 1

        return {
            "total": total,
            "average_rating": avg,
            "rating_distribution": dist,
        }
    finally:
        session.close()
