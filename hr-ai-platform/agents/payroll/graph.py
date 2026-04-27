"""Payroll Agent — LangGraph subgraph.

Flow:  parse_query → fetch_data → respond
"""

from langgraph.graph import StateGraph, START, END

from app.dependencies import get_llm_for_agent, get_memory_store
from agents.payroll.prompts import PAYROLL_RESPONSE_PROMPT
from agents.payroll.tools import fetch_salary_info
from memory.schemas import ConversationEntry
from orchestrator.state import HRState
from utils.context import build_compact_history
from utils.logger import get_logger

logger = get_logger(__name__)


def parse_query_node(state: HRState) -> dict:
    """Node: set agent identity."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Entering payroll/parse_query_node")
    try:
        return {"agent_used": "payroll_agent"}
    except Exception as e:
        logger.error(f"[{trace_id}] Error in payroll/parse_query_node: {e}")
        return {"agent_used": "payroll_agent"}


def fetch_data_node(state: HRState) -> dict:
    """Node: fetch salary data from HR skill."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Entering payroll/fetch_data_node")
    try:
        user_id = state.get("user_id", "EMP001")
        salary_info = fetch_salary_info(user_id, trace_id=trace_id)
        return {
            "metadata": {
                **state.get("metadata", {}),
                "salary_info": salary_info,
            }
        }
    except Exception as e:
        logger.error(f"[{trace_id}] Error in payroll/fetch_data_node: {e}")
        return {}


def respond_node(state: HRState) -> dict:
    """Node: generate a payroll-related response via LLM."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Entering payroll/respond_node")
    try:
        llm = get_llm_for_agent("payroll_agent")
        salary_info = state.get("metadata", {}).get(
            "salary_info", "No salary information available"
        )

        # Build conversation history string
        history_str = build_compact_history(
            state.get("conversation_history", []),
            max_turns=3,
            max_chars_per_message=220,
        )

        prompt = PAYROLL_RESPONSE_PROMPT.format(
            message=state.get("message", ""),
            salary_info=salary_info,
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
            intent=state.get("intent", "payroll_query"),
            agent_used="payroll_agent",
            privacy_mode=state.get("privacy_mode", "identified"),
            thread_id=state.get("thread_id", ""),
            trace_id=trace_id,
        )
        saved = store.save_conversation(entry)
        metadata = {
            **state.get("metadata", {}),
            "memory_persisted": bool(saved),
        }

        logger.info(f"[{trace_id}] Payroll agent response generated")
        return {"response": response_text, "metadata": metadata}

    except Exception as e:
        logger.error(f"[{trace_id}] Error in payroll/respond_node: {e}")
        return {
            "response": (
                "I'm having trouble retrieving your payroll information right now. "
                "Please try again or contact HR for assistance."
            )
        }


def build_payroll_graph():
    """Construct and compile the Payroll Agent subgraph."""
    graph = StateGraph(HRState)

    graph.add_node("parse_query", parse_query_node)
    graph.add_node("fetch_data", fetch_data_node)
    graph.add_node("respond", respond_node)

    graph.add_edge(START, "parse_query")
    graph.add_edge("parse_query", "fetch_data")
    graph.add_edge("fetch_data", "respond")
    graph.add_edge("respond", END)

    return graph.compile()
