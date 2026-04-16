"""Escalation: create HR support tickets — persisted to PostgreSQL."""

import json
from datetime import datetime, timedelta, timezone

from utils.helpers import generate_id, get_timestamp
from utils.logger import get_logger

logger = get_logger(__name__)

# SLA hours by severity
SLA_HOURS = {"critical": 1, "high": 4, "medium": 24, "low": 72}


def _get_session_factory():
    from db.connection import get_session_factory
    return get_session_factory()


def create_ticket(
    title: str,
    description: str,
    severity: str,
    assignee: str = "hr-team",
    user_id: str = "",
    trace_id: str = "",
) -> str:
    """Create an HR support ticket, persist to PostgreSQL, and return its ID.

    Args:
        title: Short ticket summary.
        description: Full details.
        severity: low / medium / high / critical.
        assignee: Person or team assigned.
        user_id: Employee who raised the ticket.
        trace_id: Request trace ID.

    Returns:
        The generated ticket ID.
    """
    from db.models import TicketModel

    ticket_id = generate_id("TKT")
    now = datetime.now(timezone.utc)
    sla_hours = SLA_HOURS.get(severity, 72)
    sla_deadline = now + timedelta(hours=sla_hours)

    try:
        session_factory = _get_session_factory()
        with session_factory() as session:
            row = TicketModel(
                ticket_id=ticket_id,
                title=title,
                description=description,
                severity=severity,
                assignee=assignee,
                status="open",
                user_id=user_id,
                trace_id=trace_id,
                sla_deadline=sla_deadline,
                sla_breached=False,
            )
            session.add(row)
            session.commit()
        logger.info(
            f"[{trace_id}] Ticket {ticket_id} created (PG) — "
            f"severity={severity}, assignee={assignee}, sla={sla_hours}h"
        )
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to save ticket to PG: {e}")

    return ticket_id


def get_ticket(ticket_id: str) -> dict | None:
    """Retrieve a ticket by ID from PostgreSQL."""
    from db.models import TicketModel

    try:
        session_factory = _get_session_factory()
        with session_factory() as session:
            row = session.query(TicketModel).filter_by(ticket_id=ticket_id).first()
            if row:
                return {
                    "ticket_id": row.ticket_id,
                    "title": row.title,
                    "description": row.description,
                    "severity": row.severity,
                    "assignee": row.assignee,
                    "status": row.status,
                    "user_id": row.user_id,
                    "trace_id": row.trace_id,
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                }
    except Exception as e:
        logger.error(f"Failed to fetch ticket {ticket_id}: {e}")
    return None


def get_tickets_by_user(user_id: str) -> list[dict]:
    """Retrieve all tickets for a user."""
    from db.models import TicketModel

    try:
        session_factory = _get_session_factory()
        with session_factory() as session:
            rows = (
                session.query(TicketModel)
                .filter_by(user_id=user_id)
                .order_by(TicketModel.created_at.desc())
                .all()
            )
            return [
                {
                    "ticket_id": r.ticket_id,
                    "title": r.title,
                    "severity": r.severity,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Failed to fetch tickets for {user_id}: {e}")
    return []


def update_ticket_status(ticket_id: str, status: str, trace_id: str = "") -> bool:
    """Update a ticket's status (open → in_progress → resolved → closed)."""
    from db.models import TicketModel

    try:
        session_factory = _get_session_factory()
        with session_factory() as session:
            row = session.query(TicketModel).filter_by(ticket_id=ticket_id).first()
            if row:
                row.status = status
                session.commit()
                logger.info(f"[{trace_id}] Ticket {ticket_id} status → {status}")
                return True
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to update ticket {ticket_id}: {e}")
    return False
