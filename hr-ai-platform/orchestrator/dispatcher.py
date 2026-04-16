"""Dispatcher — routes intents to the correct agent node."""

from orchestrator.state import HRState
from utils.logger import get_logger

logger = get_logger(__name__)

# Intent → graph node name mapping
INTENT_TO_AGENT: dict[str, str] = {
    "employee_complaint": "complaint_agent",
    "leave_request": "leave_agent",
    "payroll_query": "payroll_agent",
    "policy_question": "policy_agent",
    "general_query": "default_agent",
}


def dispatch(state: HRState) -> str:
    """Return the next graph node name based on the classified intent.

    If the target agent is deactivated, redirects to 'default_agent'
    with a service-unavailable message saved in state.
    """
    from api.routes.agents import is_agent_active, get_agent_display_name

    trace_id = state.get("trace_id", "N/A")
    intent = state.get("intent", "general_query")

    agent_name = INTENT_TO_AGENT.get(intent, "default_agent")

    # Check if the agent is active
    if agent_name != "default_agent" and not is_agent_active(agent_name):
        display_name = get_agent_display_name(agent_name)
        logger.warning(
            f"[{trace_id}] Agent '{agent_name}' is deactivated — redirecting to default"
        )
        # Store the unavailable message so the default agent can use it
        state["metadata"] = {
            **state.get("metadata", {}),
            "_agent_unavailable": True,
            "_unavailable_agent_name": display_name,
        }
        return "default_agent"

    logger.info(f"[{trace_id}] Dispatching intent='{intent}' → {agent_name}")
    return agent_name
