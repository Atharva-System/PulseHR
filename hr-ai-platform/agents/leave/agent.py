"""Leave Agent — entry point."""

from agents.leave.graph import build_leave_graph
from orchestrator.state import HRState
from utils.logger import get_logger

logger = get_logger(__name__)

_leave_graph = None


def _get_graph():
    global _leave_graph
    if _leave_graph is None:
        _leave_graph = build_leave_graph()
    return _leave_graph


def run_leave_agent(state: HRState) -> dict:
    """Run the Leave Agent subgraph and return updated state."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Leave agent started")

    try:
        graph = _get_graph()
        result = graph.invoke(state)

        logger.info(f"[{trace_id}] Leave agent completed")
        return {
            "response": result.get("response", ""),
            "agent_used": "leave_agent",
            "metadata": result.get("metadata", {}),
        }

    except Exception as e:
        logger.error(f"[{trace_id}] Error in leave agent: {e}")
        return {
            "response": (
                "I'm having trouble processing your leave request right now. "
                "Please try again or contact HR directly."
            ),
            "agent_used": "leave_agent",
        }
