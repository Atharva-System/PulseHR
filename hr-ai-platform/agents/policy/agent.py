"""Policy Agent — entry point."""

from agents.policy.graph import build_policy_graph
from orchestrator.state import HRState
from utils.logger import get_logger

logger = get_logger(__name__)

_policy_graph = None


def _get_graph():
    global _policy_graph
    if _policy_graph is None:
        _policy_graph = build_policy_graph()
    return _policy_graph


def run_policy_agent(state: HRState) -> dict:
    """Run the Policy Agent subgraph and return updated state."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Policy agent started")

    try:
        graph = _get_graph()
        result = graph.invoke(state)

        logger.info(f"[{trace_id}] Policy agent completed")
        return {
            "response": result.get("response", ""),
            "agent_used": "policy_agent",
            "metadata": result.get("metadata", {}),
        }

    except Exception as e:
        logger.error(f"[{trace_id}] Error in policy agent: {e}")
        return {
            "response": (
                "I'm unable to look up policy information right now. "
                "Please try again or contact HR directly."
            ),
            "agent_used": "policy_agent",
        }
