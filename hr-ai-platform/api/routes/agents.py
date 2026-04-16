"""Agent configuration API — manage agent active/inactive status."""

from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_authority
from db.models import UserModel
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ---------------------------------------------------------------------------
# In-memory agent registry (persists until server restart)
# For production, store in DB. This is lightweight and sufficient.
# ---------------------------------------------------------------------------

_AGENT_CONFIG: dict[str, dict] = {
    "complaint_agent": {
        "id": "complaint_agent",
        "name": "Complaint Agent",
        "description": "Handles employee complaints, harassment reports, and workplace issues. Creates tickets for HR review.",
        "intent": "employee_complaint",
        "is_active": True,
        "updated_at": None,
        "updated_by": None,
    },
    "leave_agent": {
        "id": "leave_agent",
        "name": "Leave Agent",
        "description": "Processes leave requests, checks leave balance, and provides leave policy information.",
        "intent": "leave_request",
        "is_active": True,
        "updated_at": None,
        "updated_by": None,
    },
    "payroll_agent": {
        "id": "payroll_agent",
        "name": "Payroll Agent",
        "description": "Answers salary queries, payslip requests, deductions, bonuses, and compensation questions.",
        "intent": "payroll_query",
        "is_active": True,
        "updated_at": None,
        "updated_by": None,
    },
    "policy_agent": {
        "id": "policy_agent",
        "name": "Policy Agent",
        "description": "Provides information about company HR policies, rules, guidelines, and procedures.",
        "intent": "policy_question",
        "is_active": True,
        "updated_at": None,
        "updated_by": None,
    },
    "default_agent": {
        "id": "default_agent",
        "name": "General Assistant",
        "description": "Handles greetings, general queries, and routes unknown requests. Always active.",
        "intent": "general_query",
        "is_active": True,
        "updated_at": None,
        "updated_by": None,
    },
}


# ---------------------------------------------------------------------------
# Public helper — used by dispatcher to check agent status
# ---------------------------------------------------------------------------

def is_agent_active(agent_name: str) -> bool:
    """Check if an agent is currently active."""
    config = _AGENT_CONFIG.get(agent_name)
    if config is None:
        return True  # Unknown agents default to active
    return config["is_active"]


def get_agent_display_name(agent_name: str) -> str:
    """Get the human-readable name of an agent."""
    config = _AGENT_CONFIG.get(agent_name)
    return config["name"] if config else agent_name


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AgentResponse(BaseModel):
    id: str
    name: str
    description: str
    intent: str
    is_active: bool
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


class UpdateAgentRequest(BaseModel):
    is_active: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[AgentResponse])
async def list_agents(
    current_user: UserModel = Depends(require_authority),
):
    """List all agents with their current status."""
    return [AgentResponse(**cfg) for cfg in _AGENT_CONFIG.values()]


@router.patch("/{agent_id}", response_model=AgentResponse)
async def toggle_agent(
    agent_id: str,
    body: UpdateAgentRequest,
    current_user: UserModel = Depends(require_authority),
):
    """Activate or deactivate an agent. Higher Authority only."""
    if agent_id not in _AGENT_CONFIG:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent_id == "default_agent":
        raise HTTPException(
            status_code=400,
            detail="The General Assistant cannot be deactivated — it handles fallback queries.",
        )

    config = _AGENT_CONFIG[agent_id]
    config["is_active"] = body.is_active
    config["updated_at"] = datetime.now(timezone.utc).isoformat()
    config["updated_by"] = current_user.username

    status_str = "activated" if body.is_active else "deactivated"
    logger.info(f"Agent '{agent_id}' {status_str} by {current_user.username}")

    return AgentResponse(**config)
