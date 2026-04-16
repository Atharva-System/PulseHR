"""Background task: auto-escalate tickets that breach SLA deadlines."""

import asyncio
from datetime import datetime, timezone

from db.connection import get_db_session
from db.models import TicketModel
from escalation.notifier import notify_hr, notify_authority
from escalation.audit_log import log_event
from utils.logger import get_logger

logger = get_logger(__name__)

# Check every 5 minutes
CHECK_INTERVAL_SECONDS = 300


async def sla_checker_loop():
    """Periodically check for SLA breaches and auto-escalate."""
    logger.info("SLA checker background task started (interval=%ds)", CHECK_INTERVAL_SECONDS)
    while True:
        try:
            await asyncio.to_thread(_check_and_escalate)
        except Exception as e:
            logger.error(f"SLA checker error: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def _check_and_escalate():
    """Check all open/in_progress tickets for SLA breach."""
    session = get_db_session()
    try:
        now = datetime.now(timezone.utc)
        breached_tickets = (
            session.query(TicketModel)
            .filter(
                TicketModel.status.in_(["open", "in_progress"]),
                TicketModel.sla_deadline.isnot(None),
                TicketModel.sla_deadline < now,
                TicketModel.sla_breached == False,
            )
            .all()
        )

        for ticket in breached_tickets:
            ticket.sla_breached = True

            # Auto-escalate: notify HR (and authority for critical/high)
            try:
                overdue_hours = round((now - ticket.sla_deadline).total_seconds() / 3600, 1)
                summary = (
                    f"SLA BREACH — Ticket {ticket.ticket_id} is {overdue_hours}h overdue.\n"
                    f"Title: {ticket.title}\n"
                    f"Severity: {ticket.severity}\n"
                    f"User: {ticket.user_id}\n"
                    f"Status: {ticket.status}"
                )
                # Always notify HR
                notify_hr(summary, ticket.severity)

                # For critical/high — also notify Higher Authority
                if ticket.severity in ("critical", "high"):
                    notify_authority(summary, ticket.severity)
                    logger.warning(
                        f"SLA BREACH (ESCALATED TO AUTHORITY): {ticket.ticket_id} — "
                        f"severity={ticket.severity}, {overdue_hours}h overdue"
                    )

                log_event(
                    "sla_breached",
                    {
                        "ticket_id": ticket.ticket_id,
                        "severity": ticket.severity,
                        "overdue_hours": overdue_hours,
                        "authority_notified": ticket.severity in ("critical", "high"),
                    },
                    trace_id=ticket.trace_id,
                )
                logger.warning(
                    f"SLA BREACH: {ticket.ticket_id} — {overdue_hours}h overdue"
                )
            except Exception as e:
                logger.error(f"Failed to escalate SLA breach for {ticket.ticket_id}: {e}")

        if breached_tickets:
            session.commit()
            logger.info(f"SLA checker: {len(breached_tickets)} ticket(s) marked as breached")
    finally:
        session.close()
