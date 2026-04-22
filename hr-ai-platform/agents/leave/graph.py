"""Leave Agent — LangGraph subgraph.

Flow:  parse_request → check_balance → respond
"""

from langgraph.graph import StateGraph, START, END

from app.dependencies import get_llm, get_memory_store
from agents.leave.prompts import LEAVE_RESPONSE_PROMPT
from agents.leave.tools import check_leave_balance
from memory.schemas import ConversationEntry
from orchestrator.state import HRState
from utils.logger import get_logger

logger = get_logger(__name__)


def parse_request_node(state: HRState) -> dict:
    """Node: acknowledge the leave request."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Entering leave/parse_request_node")
    try:
        return {"agent_used": "leave_agent"}
    except Exception as e:
        logger.error(f"[{trace_id}] Error in parse_request_node: {e}")
        return {"agent_used": "leave_agent"}


def check_balance_node(state: HRState) -> dict:
    """Node: fetch leave balance from HR skill."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Entering leave/check_balance_node")
    try:
        user_id = state.get("user_id", "EMP001")
        balance = check_leave_balance(user_id, trace_id=trace_id)
        return {
            "metadata": {
                **state.get("metadata", {}),
                "leave_balance": balance,
            }
        }
    except Exception as e:
        logger.error(f"[{trace_id}] Error in check_balance_node: {e}")
        return {}


def respond_node(state: HRState) -> dict:
    """Node: generate a leave-related response via LLM."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Entering leave/respond_node")
    try:
        llm = get_llm()
        balance_info = state.get("metadata", {}).get("leave_balance", "No balance info available")

        # Build conversation history string
        history_parts = []
        for entry in state.get("conversation_history", []):
            history_parts.append(f"Employee: {entry.get('content', '')}")
            history_parts.append(f"HR Assistant: {entry.get('content2', '')}")
        history_str = "\n".join(history_parts) if history_parts else "(No prior conversation)"

        prompt = LEAVE_RESPONSE_PROMPT.format(
            message=state.get("message", ""),
            balance_info=balance_info,
            history=history_str,
        )
        ai_message = llm.invoke(prompt)
        response_text = ai_message.content

        # Save to memory
        store = get_memory_store()
        entry = ConversationEntry(
            user_id=state.get("user_id", "unknown"),
            message=state.get("message", ""),
            response=response_text,
            intent=state.get("intent", "leave_request"),
            agent_used="leave_agent",
            privacy_mode=state.get("privacy_mode", "identified"),
            trace_id=trace_id,
        )
        store.save_conversation(entry)

        logger.info(f"[{trace_id}] Leave agent response generated")
        return {"response": response_text}

    except Exception as e:
        logger.error(f"[{trace_id}] Error in leave/respond_node: {e}")
        return {
            "response": (
                "I'd be happy to help with your leave request. "
                "Could you please provide your employee ID so I can check "
                "your balance? You can also contact HR directly for assistance."
            )
        }


def build_leave_graph():
    """Construct and compile the Leave Agent subgraph."""
    graph = StateGraph(HRState)

    graph.add_node("parse_request", parse_request_node)
    graph.add_node("check_balance", check_balance_node)
    graph.add_node("respond", respond_node)

    graph.add_edge(START, "parse_request")
    graph.add_edge("parse_request", "check_balance")
    graph.add_edge("check_balance", "respond")
    graph.add_edge("respond", END)

    return graph.compile()
