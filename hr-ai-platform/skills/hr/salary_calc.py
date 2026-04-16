"""Skill: salary and payroll information.

Actual salary data would come from a payroll system integration.
For now, returns general payroll information based on company policy.
"""

from skills.registry import registry
from db.connection import get_db_session
from db.models import UserModel
from utils.logger import get_logger

logger = get_logger(__name__)


@registry.tool
def get_salary_info(employee_id: str) -> dict:
    """Return salary/payroll information for an employee.

    Args:
        employee_id: Username or employee identifier.

    Returns:
        dict with payroll information.
    """
    logger.info(f"Fetching salary info for {employee_id}")
    session = get_db_session()
    try:
        user = session.query(UserModel).filter(
            (UserModel.username == employee_id) | (UserModel.id == employee_id)
        ).first()
        if user:
            return {
                "employee_id": user.username,
                "employee_name": user.full_name or user.username,
                "pay_frequency": "monthly",
                "currency": "INR",
                "note": (
                    "For detailed salary breakdown, payslip, deductions, "
                    "and bonus information, please contact the HR/Finance department "
                    "or check your payroll portal."
                ),
            }
        return {"error": f"Employee '{employee_id}' not found in the system"}
    finally:
        session.close()
