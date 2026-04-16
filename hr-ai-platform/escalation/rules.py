"""Escalation: severity-based routing rules."""

from utils.constants import EscalationAction, Severity
from utils.logger import get_logger

logger = get_logger(__name__)


def evaluate_escalation(severity: str) -> str:
    """Determine the escalation action based on severity.

    Rules:
        critical / high  → notify_hr
        medium           → create_ticket
        low              → log_only

    Args:
        severity: The complaint severity level.

    Returns:
        EscalationAction string.
    """
    severity = severity.lower()
    if severity in (Severity.CRITICAL, Severity.HIGH):
        action = EscalationAction.NOTIFY_HR
    elif severity == Severity.MEDIUM:
        action = EscalationAction.CREATE_TICKET
    else:
        action = EscalationAction.LOG_ONLY

    logger.info(f"Escalation rule: severity={severity} → action={action}")
    return action
