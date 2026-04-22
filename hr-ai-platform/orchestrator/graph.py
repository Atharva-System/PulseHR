"""Main orchestrator — LangGraph workflow.

Flow:  START → router → (dispatch) → agent → END
"""

from langgraph.graph import StateGraph, START, END

from app.dependencies import get_llm, get_memory_store
from orchestrator.state import HRState
from orchestrator.router import classify_intent
from orchestrator.dispatcher import dispatch
from api.routes.agents import is_agent_active
from agents.complaint.agent import run_complaint_agent
from agents.leave.agent import run_leave_agent
from agents.payroll.agent import run_payroll_agent
from agents.policy.agent import run_policy_agent
from memory.schemas import ConversationEntry
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Default / fallback agent (runs inline — no sub-folder needed)
# ---------------------------------------------------------------------------

def run_default_agent(state: HRState) -> dict:
    """Handle general queries and unknown intents with a friendly LLM response."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Default agent started")

    # Check if we're here because an agent was deactivated
    metadata = state.get("metadata", {})
    if metadata.get("_agent_unavailable"):
        agent_name = metadata.get("_unavailable_agent_name", "This service")
        logger.info(f"[{trace_id}] Returning service unavailable for: {agent_name}")
        return {
            "response": (
                f"I'm sorry, the **{agent_name}** service is currently unavailable. "
                "Our team is working on it. Please try again later or contact the "
                "HR department directly for assistance.\n\n"
                "📧 You can reach HR at hr@company.com or visit the HR office."
            ),
            "agent_used": "default_agent",
        }

    try:
        llm = get_llm()

        # Build conversation history string
        history_parts = []
        for entry in state.get("conversation_history", []):
            history_parts.append(f"Employee: {entry.get('content', '')}")
            history_parts.append(f"HR Assistant: {entry.get('content2', '')}")
        history_str = "\n".join(history_parts) if history_parts else ""

        history_block = ""
        if history_str:
            history_block = f"\n\nRECENT CONVERSATION HISTORY:\n{history_str}\n"

        # Build list of currently active services
        services = []
        if is_agent_active("complaint_agent"):
            services.append("complaints")
        if is_agent_active("leave_agent"):
            services.append("leave requests")
        if is_agent_active("payroll_agent"):
            services.append("payroll queries")
        if is_agent_active("policy_agent"):
            services.append("policy questions")
        services_str = ", ".join(services) if services else "general HR inquiries"

        prompt = (
            "You are a friendly but strict HR assistant. Respond to the employee's "
            "message in 1–2 short sentences. If it's a greeting, greet them back and "
            f"briefly mention you can help with {services_str}. "
            "ONLY handle HR topics (complaints, leave, payroll, policy). "
            "If the message is outside HR scope, do NOT answer that content; politely "
            "state you can only help with HR topics and ask how you can help with HR."
            f"{history_block}\n\n"
            f"EMPLOYEE MESSAGE:\n{state.get('message', '')}\n\n"
            "Keep it brief and natural. No filler phrases."
        )
        ai_message = llm.invoke(prompt)
        logger.info(f"[{trace_id}] Default agent completed")

        response_text = ai_message.content

        # Save to memory
        try:
            store = get_memory_store()
            entry = ConversationEntry(
                user_id=state.get("user_id", "unknown"),
                message=state.get("message", ""),
                response=response_text,
                intent=state.get("intent", "general_query"),
                agent_used="default_agent",
                privacy_mode=state.get("privacy_mode", "identified"),
                trace_id=trace_id,
            )
            store.save_conversation(entry)
        except Exception as save_err:
            logger.warning(f"[{trace_id}] Failed to save default agent conversation: {save_err}")

        return {
            "response": response_text,
            "agent_used": "default_agent",
        }

    except Exception as e:
        logger.error(f"[{trace_id}] Error in default_agent: {e}")
        return {
            "response": (
                "Hello! I'm your HR assistant. I can help you with complaints, "
                "leave requests, payroll queries, and company policy questions. "
                "How can I assist you today?"
            ),
            "agent_used": "default_agent",
        }


# ---------------------------------------------------------------------------
# Build the main graph
# ---------------------------------------------------------------------------

def build_graph():
    """Construct and compile the main orchestrator graph.

    Returns a compiled LangGraph that routes messages to the right agent.
    """
    graph = StateGraph(HRState)

    # --- Nodes ---
    graph.add_node("router", classify_intent)
    graph.add_node("complaint_agent", run_complaint_agent)
    graph.add_node("leave_agent", run_leave_agent)
    graph.add_node("payroll_agent", run_payroll_agent)
    graph.add_node("policy_agent", run_policy_agent)
    graph.add_node("default_agent", run_default_agent)

    # --- Edges ---
    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", dispatch)

    # Every agent terminates the graph
    graph.add_edge("complaint_agent", END)
    graph.add_edge("leave_agent", END)
    graph.add_edge("payroll_agent", END)
    graph.add_edge("policy_agent", END)
    graph.add_edge("default_agent", END)

    compiled = graph.compile()
    logger.info("Orchestrator graph compiled successfully")
    return compiled
