"""Complaint Agent tools — thin wrappers delegating to skills / escalation."""

from app.dependencies import get_memory_store
from escalation.ticketing import create_ticket
from escalation.notifier import notify_hr as _notify_hr
from escalation.audit_log import log_event
from memory.schemas import ComplaintRecord
from utils.logger import get_logger

logger = get_logger(__name__)


def create_hr_ticket(
    user_id: str,
    complaint_type: str,
    severity: str,
    message: str,
    privacy_mode: str = "identified",
    complaint_target: str = "",
    trace_id: str = "",
) -> str:
    """Create an HR ticket for a complaint.

    Returns:
        The ticket ID.
    """
    logger.info(f"[{trace_id}] Creating HR ticket for user {user_id}")
    ticket_id = create_ticket(
        title=f"Employee Complaint — {complaint_type}",
        description=message,
        severity=severity,
        user_id=user_id,
        privacy_mode=privacy_mode,
        complaint_target=complaint_target,
        trace_id=trace_id,
    )
    log_event(
        "ticket_created",
        {"user_id": user_id, "ticket_id": ticket_id, "severity": severity},
        trace_id=trace_id,
    )
    return ticket_id


def notify_hr_tool(complaint_summary: str, severity: str, trace_id: str = "") -> dict:
    """Notify HR team about a complaint.

    Returns:
        Notification result dict.
    """
    logger.info(f"[{trace_id}] Notifying HR — severity={severity}")
    result = _notify_hr(complaint_summary, severity)
    log_event(
        "hr_notified",
        {"severity": severity, "summary_preview": complaint_summary[:100]},
        trace_id=trace_id,
    )
    return result


def log_complaint(
    user_id: str,
    message: str,
    complaint_type: str,
    emotion: str,
    severity: str,
    privacy_mode: str = "identified",
    complaint_target: str = "",
    escalation_action: str = "",
    ticket_id: str = "",
    trace_id: str = "",
) -> None:
    """Persist a complaint record to memory."""
    logger.info(f"[{trace_id}] Logging complaint for user {user_id}")
    store = get_memory_store()
    record = ComplaintRecord(
        user_id=user_id,
        message=message,
        complaint_type=complaint_type,
        emotion=emotion,
        severity=severity,
        privacy_mode=privacy_mode,
        complaint_target=complaint_target,
        escalation_action=escalation_action,
        ticket_id=ticket_id,
        trace_id=trace_id,
    )
    store.save_complaint(record)
    log_event(
        "complaint_logged",
        {"user_id": user_id, "complaint_id": record.complaint_id},
        trace_id=trace_id,
    )
