"""Complaint Agent escalation handler — routes by severity."""

from escalation.rules import evaluate_escalation
from agents.complaint.tools import create_hr_ticket, notify_hr_tool, log_complaint
from orchestrator.state import HRState
from utils.privacy import is_complaint_about_hr
from utils.logger import get_logger

logger = get_logger(__name__)


def handle_escalation(state: HRState) -> dict:
    """Evaluate severity and execute the right escalation action.

    If the complaint targets HR staff, the ticket is created immediately
    and only admin (higher_authority) is notified — HR never sees it.

    Returns dict with: escalation_action (and optionally ticket_id in metadata).
    """
    trace_id = state.get("trace_id", "N/A")
    severity = state.get("severity", "low")
    user_id = state.get("user_id", "unknown")
    message = state.get("message", "")
    complaint_type = state.get("complaint_type", "other")
    emotion = state.get("emotion", "neutral")
    privacy_mode = state.get("privacy_mode", "identified")
    complaint_target = state.get("complaint_target", "")
    hr_targeted = bool(complaint_target and is_complaint_about_hr(complaint_target))

    logger.info(f"[{trace_id}] Escalation handler — severity={severity}, hr_targeted={hr_targeted}")

    try:
        action = evaluate_escalation(severity)
        ticket_id = ""

        if hr_targeted:
            # ── HR-targeted complaint: create ticket + notify admin ONLY ──
            ticket_id = create_hr_ticket(
                user_id=user_id,
                complaint_type=complaint_type,
                severity=severity,
                message=message,
                privacy_mode=privacy_mode,
                complaint_target=complaint_target,
                trace_id=trace_id,
            )
            # Notify only higher_authority (never HR)
            try:
                from escalation.notifier import notify_authority_hr_complaint
                notify_authority_hr_complaint(
                    complaint_summary=f"[{complaint_type}] {message[:300]}",
                    severity=severity,
                    complaint_target=complaint_target,
                    ticket_id=ticket_id,
                    user_id=user_id,
                )
                logger.info(f"[{trace_id}] Admin notified — HR-targeted complaint ticket={ticket_id}")
            except Exception as _err:
                logger.error(f"[{trace_id}] Failed to notify admin for HR-targeted complaint: {_err}")
            action = "escalate_to_admin"  # override action label

        elif action == "notify_hr":
            notify_hr_tool(
                complaint_summary=f"[{complaint_type}] {message[:200]}",
                severity=severity,
                trace_id=trace_id,
            )
            ticket_id = create_hr_ticket(
                user_id=user_id,
                complaint_type=complaint_type,
                severity=severity,
                message=message,
                privacy_mode=privacy_mode,
                complaint_target=complaint_target,
                trace_id=trace_id,
            )
        elif action == "create_ticket":
            ticket_id = create_hr_ticket(
                user_id=user_id,
                complaint_type=complaint_type,
                severity=severity,
                message=message,
                privacy_mode=privacy_mode,
                complaint_target=complaint_target,
                trace_id=trace_id,
            )

        # Always log the complaint
        log_complaint(
            user_id=user_id,
            message=message,
            complaint_type=complaint_type,
            emotion=emotion,
            severity=severity,
            privacy_mode=privacy_mode,
            complaint_target=complaint_target,
            escalation_action=action,
            ticket_id=ticket_id,
            trace_id=trace_id,
        )

        logger.info(f"[{trace_id}] Escalation action: {action}, ticket_id: {ticket_id}")
        return {
            "escalation_action": action,
            "metadata": {
                **state.get("metadata", {}),
                "ticket_id": ticket_id,
            },
        }

    except Exception as e:
        logger.error(f"[{trace_id}] Error in handle_escalation: {e}")
        return {"escalation_action": "log_only"}
