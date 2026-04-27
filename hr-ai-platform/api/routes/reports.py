"""Reports API routes — analytics and summaries for HR / Higher Authority."""

from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.auth import require_hr
from db.connection import get_db_session
from db.models import TicketModel, ConversationModel, ComplaintModel, UserModel
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SummaryResponse(BaseModel):
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    critical_tickets: int
    total_conversations: int
    total_complaints: int
    unique_users: int
    resolution_rate: float  # percentage
    severity_breakdown: dict
    intent_distribution: dict
    daily_trends: list[dict]


class AgentReportResponse(BaseModel):
    agents: list[dict]
    total_handled: int


class ComplaintTargetReportItem(BaseModel):
    target_key: str
    target_user_id: str = ""
    target_name: str
    total_tickets: int
    open_tickets: int
    closed_tickets: int
    high_priority_tickets: int
    severity_breakdown: dict
    status_breakdown: dict
    last_ticket_at: Optional[str] = None


def _allowed_report_levels(current_user: UserModel) -> set[str] | None:
    if current_user.role == "higher_authority":
        return None
    if not current_user.receive_notifications:
        return set()
    return {
        (level or "").strip().lower()
        for level in (current_user.notification_levels or "").split(",")
        if (level or "").strip()
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=SummaryResponse)
async def summary(
    days: int = Query(30, ge=1, le=365, description="Look-back period in days"),
    current_user: UserModel = Depends(require_hr),
):
    """Overall platform summary with trends."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    session = get_db_session()
    try:
        # Tickets
        tickets = session.query(TicketModel).filter(
            TicketModel.created_at >= since
        ).all()
        total_tickets = len(tickets)
        open_tickets = sum(1 for t in tickets if t.status in ("open", "in_progress"))
        resolved_tickets = sum(1 for t in tickets if t.status in ("resolved", "closed"))
        critical_tickets = sum(1 for t in tickets if t.severity in ("critical", "high"))
        resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets else 0.0

        severity_breakdown: dict[str, int] = {}
        for t in tickets:
            sev = t.severity or "unknown"
            severity_breakdown[sev] = severity_breakdown.get(sev, 0) + 1

        # Conversations
        conversations = session.query(ConversationModel).filter(
            ConversationModel.timestamp >= since
        ).all()
        unique_users = len({c.user_id for c in conversations})

        intent_distribution: dict[str, int] = {}
        for c in conversations:
            intent = c.intent or "unknown"
            intent_distribution[intent] = intent_distribution.get(intent, 0) + 1

        # Complaints
        complaints = session.query(ComplaintModel).filter(
            ComplaintModel.timestamp >= since
        ).all()

        # Daily trends (tickets created per day)
        daily_map: dict[str, int] = {}
        for t in tickets:
            day = t.created_at.strftime("%Y-%m-%d") if t.created_at else "unknown"
            daily_map[day] = daily_map.get(day, 0) + 1

        daily_trends = [
            {"date": d, "count": c}
            for d, c in sorted(daily_map.items())
        ]

        return SummaryResponse(
            total_tickets=total_tickets,
            open_tickets=open_tickets,
            resolved_tickets=resolved_tickets,
            critical_tickets=critical_tickets,
            total_conversations=len(conversations),
            total_complaints=len(complaints),
            unique_users=unique_users,
            resolution_rate=round(resolution_rate, 1),
            severity_breakdown=severity_breakdown,
            intent_distribution=intent_distribution,
            daily_trends=daily_trends,
        )
    finally:
        session.close()


@router.get("/agents", response_model=AgentReportResponse)
async def agent_report(
    days: int = Query(30, ge=1, le=365),
    current_user: UserModel = Depends(require_hr),
):
    """Agent usage and performance report."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    session = get_db_session()
    try:
        conversations = session.query(ConversationModel).filter(
            ConversationModel.timestamp >= since
        ).all()

        agent_map: dict[str, dict] = {}
        for c in conversations:
            agent = c.agent_used or "unknown"
            if agent not in agent_map:
                agent_map[agent] = {"agent": agent, "count": 0, "intents": {}}
            agent_map[agent]["count"] += 1
            intent = c.intent or "unknown"
            agent_map[agent]["intents"][intent] = agent_map[agent]["intents"].get(intent, 0) + 1

        agents = sorted(agent_map.values(), key=lambda x: x["count"], reverse=True)

        return AgentReportResponse(
            agents=agents,
            total_handled=len(conversations),
        )
    finally:
        session.close()


@router.get("/tickets")
async def ticket_report(
    days: int = Query(30, ge=1, le=365),
    current_user: UserModel = Depends(require_hr),
):
    """Detailed ticket analytics with date range."""
    since = datetime.now(timezone.utc) - timedelta(days=days)

    session = get_db_session()
    try:
        tickets = session.query(TicketModel).filter(
            TicketModel.created_at >= since
        ).all()

        # Group by day
        daily: dict[str, dict] = {}
        for t in tickets:
            day = t.created_at.strftime("%Y-%m-%d") if t.created_at else "unknown"
            if day not in daily:
                daily[day] = {"date": day, "created": 0, "resolved": 0, "critical": 0}
            daily[day]["created"] += 1
            if t.status in ("resolved", "closed"):
                daily[day]["resolved"] += 1
            if t.severity in ("critical", "high"):
                daily[day]["critical"] += 1

        return {
            "period_days": days,
            "total_tickets": len(tickets),
            "daily": sorted(daily.values(), key=lambda x: x["date"]),
        }
    finally:
        session.close()


@router.get("/complaint-targets", response_model=list[ComplaintTargetReportItem])
async def complaint_target_report(
    days: int = Query(30, ge=1, le=365),
    current_user: UserModel = Depends(require_hr),
):
    """Aggregate complaint tickets by the person the complaint is about."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    allowed_levels = _allowed_report_levels(current_user)

    session = get_db_session()
    try:
        q = session.query(TicketModel).filter(
            TicketModel.created_at >= since,
            TicketModel.complaint_target != "",
        )
        if allowed_levels is not None:
            if not allowed_levels:
                return []
            q = q.filter(TicketModel.severity.in_(sorted(allowed_levels)))

        tickets = q.order_by(TicketModel.created_at.desc()).all()
        grouped: dict[str, dict] = {}

        for t in tickets:
            target_user_id = (getattr(t, "complaint_target_user_id", "") or "").strip()
            target_name = (getattr(t, "complaint_target", "") or "").strip()
            if not target_name:
                continue

            group_key = target_user_id or target_name.lower()
            if group_key not in grouped:
                grouped[group_key] = {
                    "target_key": group_key,
                    "target_user_id": target_user_id,
                    "target_name": target_name,
                    "total_tickets": 0,
                    "open_tickets": 0,
                    "closed_tickets": 0,
                    "high_priority_tickets": 0,
                    "severity_breakdown": {},
                    "status_breakdown": {},
                    "last_ticket_at": None,
                }

            item = grouped[group_key]
            item["total_tickets"] += 1

            sev = (t.severity or "unknown").lower()
            status = (t.status or "unknown").lower()
            item["severity_breakdown"][sev] = item["severity_breakdown"].get(sev, 0) + 1
            item["status_breakdown"][status] = item["status_breakdown"].get(status, 0) + 1

            if status in ("open", "in_progress"):
                item["open_tickets"] += 1
            if status == "closed":
                item["closed_tickets"] += 1
            if sev in ("high", "critical"):
                item["high_priority_tickets"] += 1

            created_at = t.created_at.isoformat() if t.created_at else None
            if created_at and (item["last_ticket_at"] is None or created_at > item["last_ticket_at"]):
                item["last_ticket_at"] = created_at

        result = sorted(
            grouped.values(),
            key=lambda item: (
                -item["total_tickets"],
                -item["high_priority_tickets"],
                item["target_name"].lower(),
            ),
        )
        return [ComplaintTargetReportItem(**item) for item in result]
    finally:
        session.close()
