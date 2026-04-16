"""Payroll Agent — entry point."""

from agents.payroll.graph import build_payroll_graph
from orchestrator.state import HRState
from utils.logger import get_logger

logger = get_logger(__name__)

_payroll_graph = None


def _get_graph():
    global _payroll_graph
    if _payroll_graph is None:
        _payroll_graph = build_payroll_graph()
    return _payroll_graph


def run_payroll_agent(state: HRState) -> dict:
    """Run the Payroll Agent subgraph and return updated state."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Payroll agent started")

    try:
        graph = _get_graph()
        result = graph.invoke(state)

        logger.info(f"[{trace_id}] Payroll agent completed")
        return {
            "response": result.get("response", ""),
            "agent_used": "payroll_agent",
            "metadata": result.get("metadata", {}),
        }

    except Exception as e:
        logger.error(f"[{trace_id}] Error in payroll agent: {e}")
        return {
            "response": (
                "I'm having trouble processing your payroll query right now. "
                "Please try again or contact HR directly."
            ),
            "agent_used": "payroll_agent",
        }
