"""Policy Agent — LangGraph subgraph.

Flow:  search_policy → respond
"""

from langgraph.graph import StateGraph, START, END

from app.dependencies import get_llm_for_agent, get_memory_store
from agents.policy.tools import search_policies
from memory.schemas import ConversationEntry
from orchestrator.state import HRState
from utils.context import build_compact_history
from utils.logger import get_logger

logger = get_logger(__name__)

POLICY_RESPONSE_PROMPT = """\
You are an HR policy assistant. Answer using ONLY the official policy info below.

RECENT CONVERSATION HISTORY:
{history}

EMPLOYEE QUESTION:
{message}

RELEVANT COMPANY POLICIES:
{policy_info}

RULES:
1. Answer based ONLY on the policies provided — never make up rules
2. Quote specific numbers (days, hours, etc.) from the policy
3. If the policy doesn’t cover it, say so and suggest contacting HR
4. Use bullet points only when listing 3+ items
5. Keep answers to 2–3 sentences unless the policy details require more
6. Use conversation history for context on follow-ups
7. If the user asks something outside company policy scope, do not answer that
    topic; clearly state you can only help with official HR policies.

Respond:
"""


def search_policy_node(state: HRState) -> dict:
    """Node: search for relevant policies."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Entering policy/search_policy_node")
    try:
        policy_info = search_policies(
            state.get("message", ""), trace_id=trace_id
        )
        return {
            "agent_used": "policy_agent",
            "metadata": {
                **state.get("metadata", {}),
                "policy_info": policy_info,
            },
        }
    except Exception as e:
        logger.error(f"[{trace_id}] Error in policy/search_policy_node: {e}")
        return {"agent_used": "policy_agent"}


def respond_node(state: HRState) -> dict:
    """Node: generate a policy response via LLM."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Entering policy/respond_node")
    try:
        llm = get_llm_for_agent("policy_agent")
        policy_info = state.get("metadata", {}).get(
            "policy_info", "No policy information available"
        )

        # Build conversation history string
        history_str = build_compact_history(
            state.get("conversation_history", []),
            max_turns=3,
            max_chars_per_message=220,
        )

        prompt = POLICY_RESPONSE_PROMPT.format(
            message=state.get("message", ""),
            policy_info=policy_info,
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
            intent=state.get("intent", "policy_question"),
            agent_used="policy_agent",
            privacy_mode=state.get("privacy_mode", "identified"),
            thread_id=state.get("thread_id", ""),
            trace_id=trace_id,
        )
        saved = store.save_conversation(entry)
        metadata = {
            **state.get("metadata", {}),
            "memory_persisted": bool(saved),
        }

        logger.info(f"[{trace_id}] Policy agent response generated")
        return {"response": response_text, "metadata": metadata}

    except Exception as e:
        logger.error(f"[{trace_id}] Error in policy/respond_node: {e}")
        return {
            "response": (
                "I'm having trouble looking up that policy right now. "
                "Please try again or contact HR for assistance."
            )
        }


def build_policy_graph():
    """Construct and compile the Policy Agent subgraph."""
    graph = StateGraph(HRState)

    graph.add_node("search_policy", search_policy_node)
    graph.add_node("respond", respond_node)

    graph.add_edge(START, "search_policy")
    graph.add_edge("search_policy", "respond")
    graph.add_edge("respond", END)

    return graph.compile()
