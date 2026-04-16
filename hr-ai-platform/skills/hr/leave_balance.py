"""Skill: check employee leave balance.

Leave entitlements are based on company HR policy:
- Annual leave: 18 days per calendar year
- Sick leave: 12 days per calendar year
- Personal leave: 3 days per calendar year

Actual usage tracking would require integration with an HR system.
For now, returns the policy-based entitlements.
"""

from skills.registry import registry
from db.connection import get_db_session
from db.models import UserModel
from utils.logger import get_logger

logger = get_logger(__name__)

# Company-wide leave entitlements (from HR Policy)
_ANNUAL_ENTITLEMENT = 18
_SICK_ENTITLEMENT = 12
_PERSONAL_ENTITLEMENT = 3


@registry.tool
def get_leave_balance(employee_id: str) -> dict:
    """Return leave balance for an employee based on company policy.

    Args:
        employee_id: Username or employee identifier.

    Returns:
        dict with leave balance breakdown.
    """
    logger.info(f"Checking leave balance for {employee_id}")
    session = get_db_session()
    try:
        user = session.query(UserModel).filter(
            (UserModel.username == employee_id) | (UserModel.id == employee_id)
        ).first()
        if user:
            return {
                "employee_id": user.username,
                "employee_name": user.full_name or user.username,
                "annual_entitlement": _ANNUAL_ENTITLEMENT,
                "sick_entitlement": _SICK_ENTITLEMENT,
                "personal_entitlement": _PERSONAL_ENTITLEMENT,
                "total_entitlement": _ANNUAL_ENTITLEMENT + _SICK_ENTITLEMENT + _PERSONAL_ENTITLEMENT,
                "note": (
                    "These are your annual entitlements as per company HR policy. "
                    "For exact remaining balance including used days, please check "
                    "with the HR department or your HR portal."
                ),
            }
        return {"error": f"Employee '{employee_id}' not found in the system"}
    finally:
        session.close()
