"""Skill: retrieve employee details from database."""

from skills.registry import registry
from db.connection import get_db_session
from db.models import UserModel
from utils.logger import get_logger

logger = get_logger(__name__)


@registry.tool
def get_employee_details(employee_id: str) -> dict:
    """Return employee profile data from the database.

    Args:
        employee_id: Username or employee identifier.

    Returns:
        dict with employee profile or error message.
    """
    logger.info(f"Fetching employee details for {employee_id}")
    session = get_db_session()
    try:
        user = session.query(UserModel).filter(
            (UserModel.username == employee_id) | (UserModel.id == employee_id)
        ).first()
        if user:
            return {
                "employee_id": user.username,
                "name": user.full_name or user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "joined": user.created_at.isoformat() if user.created_at else "N/A",
            }
        return {"error": f"Employee '{employee_id}' not found in the system"}
    finally:
        session.close()
