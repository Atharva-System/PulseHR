"""Complaint Agent — entry point."""

from agents.complaint.graph import build_complaint_graph
from orchestrator.state import HRState
from utils.logger import get_logger

logger = get_logger(__name__)

# Compile the subgraph once at module level
_complaint_graph = None


def _get_graph():
    global _complaint_graph
    if _complaint_graph is None:
        _complaint_graph = build_complaint_graph()
    return _complaint_graph


def run_complaint_agent(state: HRState) -> dict:
    """Run the full complaint subgraph and return updated state.

    Sets agent_used = 'complaint_agent' and invokes the compiled
    LangGraph subgraph (classify → safety → respond → escalate → memory).
    """
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Complaint agent started")

    try:
        state_update = {"agent_used": "complaint_agent"}
        merged = {**state, **state_update}

        graph = _get_graph()
        result = graph.invoke(merged)

        logger.info(f"[{trace_id}] Complaint agent completed")
        return {
            "response": result.get("response", ""),
            "emotion": result.get("emotion", ""),
            "severity": result.get("severity", ""),
            "complaint_type": result.get("complaint_type", ""),
            "escalation_action": result.get("escalation_action", ""),
            "agent_used": "complaint_agent",
            "metadata": result.get("metadata", {}),
        }

    except Exception as e:
        logger.error(f"[{trace_id}] Error in complaint agent: {e}")
        return {
            "response": (
                "I'm sorry, I encountered an issue while processing your complaint. "
                "Your concern is important — please try again or contact HR directly."
            ),
            "agent_used": "complaint_agent",
        }
