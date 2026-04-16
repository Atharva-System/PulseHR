"""Payroll Agent tools — delegate to HR skills."""

from skills.hr.salary_calc import get_salary_info
from utils.logger import get_logger

logger = get_logger(__name__)


def fetch_salary_info(employee_id: str, trace_id: str = "") -> dict:
    """Retrieve salary information for an employee."""
    logger.info(f"[{trace_id}] Fetching salary info for {employee_id}")
    return get_salary_info(employee_id)


def get_payslip(employee_id: str, month: str = "", trace_id: str = "") -> dict:
    """Retrieve a payslip (placeholder).

    In production, this would query payroll software.
    """
    logger.info(f"[{trace_id}] Fetching payslip for {employee_id}, month={month}")
    return {
        "employee_id": employee_id,
        "month": month or "current",
        "status": "Payslip data would be retrieved from payroll system",
    }
