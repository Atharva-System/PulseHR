"""Leave Agent tools — delegate to HR skills."""

from skills.hr.leave_balance import get_leave_balance
from utils.logger import get_logger

logger = get_logger(__name__)


def check_leave_balance(employee_id: str, trace_id: str = "") -> dict:
    """Check remaining leave balance for an employee."""
    logger.info(f"[{trace_id}] Checking leave balance for {employee_id}")
    return get_leave_balance(employee_id)


def submit_leave_request(
    employee_id: str,
    leave_type: str,
    days: int,
    reason: str = "",
    trace_id: str = "",
) -> dict:
    """Submit a leave request (placeholder).

    In production this would write to an HR system / database.
    """
    logger.info(
        f"[{trace_id}] Leave request submitted — "
        f"employee={employee_id}, type={leave_type}, days={days}"
    )
    return {
        "status": "submitted",
        "employee_id": employee_id,
        "leave_type": leave_type,
        "days": days,
        "reason": reason,
    }
