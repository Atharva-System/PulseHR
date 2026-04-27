"""Repository for agent configuration CRUD operations."""

from datetime import datetime, timezone
from typing import Optional

from db.connection import get_db_session
from db.models import AgentConfigModel
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Default agent definitions (used for seeding)
# ---------------------------------------------------------------------------

DEFAULT_AGENTS: list[dict] = [
    {
        "id": "complaint_agent",
        "name": "Complaint Agent",
        "description": "Handles employee complaints, harassment reports, and workplace issues. Creates tickets for HR review.",
        "intent": "employee_complaint",
    },
    {
        "id": "leave_agent",
        "name": "Leave Agent",
        "description": "Processes leave requests, checks leave balance, and provides leave policy information.",
        "intent": "leave_request",
    },
    {
        "id": "payroll_agent",
        "name": "Payroll Agent",
        "description": "Answers salary queries, payslip requests, deductions, bonuses, and compensation questions.",
        "intent": "payroll_query",
    },
    {
        "id": "policy_agent",
        "name": "Policy Agent",
        "description": "Provides information about company HR policies, rules, guidelines, and procedures.",
        "intent": "policy_question",
    },
    {
        "id": "default_agent",
        "name": "General Assistant",
        "description": "Handles greetings, general queries, and routes unknown requests. Always active.",
        "intent": "general_query",
    },
]


def seed_agent_configs(default_model: str) -> None:
    """Insert default agent rows if they don't already exist.

    Called once during application startup.
    """
    session = get_db_session()
    try:
        existing_ids = {
            row.id for row in session.query(AgentConfigModel.id).all()
        }
        for agent in DEFAULT_AGENTS:
            if agent["id"] not in existing_ids:
                session.add(AgentConfigModel(
                    id=agent["id"],
                    name=agent["name"],
                    description=agent["description"],
                    intent=agent["intent"],
                    is_active=True,
                    model_name=default_model,
                    temperature=1.0,
                    top_p=1.0,
                    max_tokens=4096,
                ))
                logger.info("Seeded agent config: %s", agent["id"])
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error("Failed to seed agent configs: %s", e)
        raise
    finally:
        session.close()


def get_all_agent_configs() -> list[dict]:
    """Return all agent configs as dicts."""
    session = get_db_session()
    try:
        rows = session.query(AgentConfigModel).order_by(AgentConfigModel.id).all()
        return [r.to_dict() for r in rows]
    finally:
        session.close()


def get_agent_config(agent_id: str) -> Optional[dict]:
    """Return a single agent config dict, or None if not found."""
    session = get_db_session()
    try:
        row = session.query(AgentConfigModel).filter_by(id=agent_id).first()
        return row.to_dict() if row else None
    finally:
        session.close()


def update_agent_config(agent_id: str, updates: dict, username: str) -> Optional[dict]:
    """Apply partial updates to an agent config. Returns updated dict or None."""
    session = get_db_session()
    try:
        row = session.query(AgentConfigModel).filter_by(id=agent_id).first()
        if row is None:
            return None

        for key in ("is_active", "model_name", "temperature", "top_p", "max_tokens"):
            if key in updates and updates[key] is not None:
                setattr(row, key, updates[key])

        row.updated_by = username
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(row)
        return row.to_dict()
    except Exception as e:
        session.rollback()
        logger.error("Failed to update agent config %s: %s", agent_id, e)
        raise
    finally:
        session.close()


def is_agent_active(agent_id: str) -> bool:
    """Check if an agent is currently active (DB lookup)."""
    session = get_db_session()
    try:
        row = session.query(AgentConfigModel.is_active).filter_by(id=agent_id).first()
        if row is None:
            return True  # unknown agents default to active
        return row.is_active
    finally:
        session.close()


def get_agent_model_params(agent_id: str) -> dict:
    """Return model parameters for a given agent.

    Used by dependencies.get_llm_for_agent().
    Falls back to defaults when the agent is not in the DB.
    """
    session = get_db_session()
    try:
        row = session.query(AgentConfigModel).filter_by(id=agent_id).first()
        if row is None:
            from app.config import settings
            return {
                "model_name": settings.model_name,
                "temperature": 1.0,
                "top_p": 1.0,
                "max_tokens": 4096,
            }
        return {
            "model_name": row.model_name,
            "temperature": row.temperature,
            "top_p": row.top_p,
            "max_tokens": int(row.max_tokens),
        }
    finally:
        session.close()
