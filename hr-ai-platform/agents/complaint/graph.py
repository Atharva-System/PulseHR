"""Complaint Agent — LangGraph subgraph with conversational info gathering.

Graph flow:
    classify → safety_check → load_history → check_completeness →
        if GATHERING: ask_followup → save_to_memory
        if COMPLETE:  generate_summary → escalate → enrich_response → save_to_memory
"""

from langgraph.graph import StateGraph, START, END

from app.dependencies import get_llm, get_memory_store
from agents.complaint.classifier import classify_complaint
from agents.complaint.escalation import handle_escalation
from agents.complaint.prompts import (
    SAFETY_CHECK_PROMPT,
    RESPONSE_PROMPT,
    INFO_COMPLETENESS_PROMPT,
    FOLLOWUP_PROMPT,
    CONFIRMATION_PROMPT,
    TICKET_SUMMARY_PROMPT,
    WARM_CLOSING_PROMPT,
    POLICY_VIOLATION_CHECK_PROMPT,
)
from agents.complaint.schemas import SafetyCheckResult, InfoCompletenessResult, PolicyViolationResult
from agents.policy.tools import search_policies
from memory.schemas import ConversationEntry
from orchestrator.state import HRState
from db.connection import get_db_session
from db.models import ConversationModel
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_recent_complaint_history(user_id: str, limit: int = 10) -> str:
    """Load recent complaint conversations for the user from DB."""
    session = get_db_session()
    try:
        rows = (
            session.query(ConversationModel)
            .filter(
                ConversationModel.user_id == user_id,
                ConversationModel.intent == "employee_complaint",
            )
            .order_by(ConversationModel.timestamp.desc())
            .limit(limit)
            .all()
        )
        if not rows:
            return ""

        rows.reverse()  # chronological order
        parts = []
        for r in rows:
            parts.append(f"Employee: {r.message}")
            parts.append(f"HR Assistant: {r.response}")
        return "\n".join(parts)
    finally:
        session.close()


def _load_max_severity(user_id: str) -> str:
    """Load the highest severity from recent complaint conversations.

    This prevents short follow-up messages like 'no' or 'ok' from
    downgrading the severity that was set during the original complaint.
    """
    severity_order = ["low", "medium", "high", "critical"]
    session = get_db_session()
    try:
        rows = (
            session.query(ConversationModel.severity)
            .filter(
                ConversationModel.user_id == user_id,
                ConversationModel.intent == "employee_complaint",
                ConversationModel.severity != "",
                ConversationModel.severity.isnot(None),
            )
            .order_by(ConversationModel.timestamp.desc())
            .limit(10)
            .all()
        )
        if not rows:
            return ""

        max_idx = -1
        for (sev,) in rows:
            if sev and sev.lower() in severity_order:
                idx = severity_order.index(sev.lower())
                if idx > max_idx:
                    max_idx = idx

        return severity_order[max_idx] if max_idx >= 0 else ""
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

def classify_node(state: HRState) -> dict:
    """Node: classify complaint type, emotion, severity."""
    logger.info(f"[{state.get('trace_id', 'N/A')}] Entering classify_node")
    try:
        return classify_complaint(state)
    except Exception as e:
        logger.error(f"[{state.get('trace_id', 'N/A')}] Error in classify_node: {e}")
        return {"complaint_type": "other", "emotion": "neutral", "severity": "medium"}


def safety_check_node(state: HRState) -> dict:
    """Node: check if complaint involves immediate danger."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Entering safety_check_node")
    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(SafetyCheckResult)
        prompt = SAFETY_CHECK_PROMPT.format(
            message=state.get("message", ""),
            complaint_type=state.get("complaint_type", "other"),
            severity=state.get("severity", "medium"),
        )
        result: SafetyCheckResult = structured_llm.invoke(prompt)
        logger.info(f"[{trace_id}] Safety check: immediate_danger={result.is_immediate_danger}")

        if result.is_immediate_danger:
            return {"severity": "critical"}
        return {}

    except Exception as e:
        logger.error(f"[{trace_id}] Error in safety_check_node: {e}")
        return {}


def load_history_node(state: HRState) -> dict:
    """Node: load recent complaint conversation history for this user."""
    trace_id = state.get("trace_id", "N/A")
    user_id = state.get("user_id", "unknown")
    logger.info(f"[{trace_id}] Loading complaint history for {user_id}")

    history = _load_recent_complaint_history(user_id)

    # Also load the highest severity from previous conversation turns
    # so short follow-up messages ("no", "ok") don't downgrade it
    stored_severity = _load_max_severity(user_id)

    return {
        "metadata": {
            **state.get("metadata", {}),
            "_complaint_history": history,
            "_stored_severity": stored_severity,
        }
    }


def policy_check_node(state: HRState) -> dict:
    """Node: check if the complaint matches a company policy violation.

    If the complaint clearly violates a known company policy (e.g. POSH,
    anti-harassment, workplace conduct), flag it so the flow fast-tracks
    to confirmation + ticket instead of asking many follow-up questions.
    """
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Checking complaint against company policies")

    metadata = state.get("metadata", {})
    message = state.get("message", "")
    history = metadata.get("_complaint_history", "")

    # Only run on first message — follow-ups already have context
    is_first_message = not history or history.strip() == ""
    if not is_first_message:
        logger.info(f"[{trace_id}] Not first message, skipping policy check")
        return {}

    try:
        # Search policies relevant to the complaint
        policy_info = search_policies(message, trace_id=trace_id)

        llm = get_llm()
        structured_llm = llm.with_structured_output(PolicyViolationResult)
        prompt = POLICY_VIOLATION_CHECK_PROMPT.format(
            message=message,
            policies=policy_info,
        )
        result: PolicyViolationResult = structured_llm.invoke(prompt)
        logger.info(
            f"[{trace_id}] Policy check: violation={result.is_policy_violation}, "
            f"policy={result.matched_policy}"
        )

        if result.is_policy_violation:
            # Bump severity to at least "high" for policy violations
            severity_order = ["low", "medium", "high", "critical"]
            current = state.get("severity", "medium")
            current_idx = severity_order.index(current) if current in severity_order else 1
            new_severity = severity_order[max(current_idx, 2)]  # at least "high"

            return {
                "metadata": {
                    **metadata,
                    "_policy_violation": True,
                    "_matched_policy": result.matched_policy,
                    "_policy_summary": result.policy_summary,
                },
                "severity": new_severity,
            }
        return {}

    except Exception as e:
        logger.error(f"[{trace_id}] Error in policy_check_node: {e}")
        return {}


def check_completeness_node(state: HRState) -> dict:
    """Node: use LLM to decide if we have enough info or need to ask more."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Checking info completeness")

    metadata = state.get("metadata", {})
    history = metadata.get("_complaint_history", "")
    message = state.get("message", "")
    severity = state.get("severity", "medium")
    stored_severity = metadata.get("_stored_severity", "")

    # Restore severity from conversation history if current is lower
    # (prevents short follow-ups like "no" from downgrading severity)
    severity_order = ["low", "medium", "high", "critical"]
    if stored_severity and stored_severity in severity_order:
        current_idx = severity_order.index(severity) if severity in severity_order else 1
        stored_idx = severity_order.index(stored_severity)
        if stored_idx > current_idx:
            logger.info(
                f"[{trace_id}] Restoring severity: {severity} → {stored_severity} (from history)"
            )
            severity = stored_severity

    # Immediate danger → skip gathering, go straight to ticket
    if severity == "critical":
        logger.info(f"[{trace_id}] Critical severity → skipping info gathering")
        return {
            "severity": severity,
            "metadata": {
                **metadata,
                "_info_status": "COMPLETE",
                "_missing_info": [],
            }
        }

    # Policy violation OR high severity → fast-track to CONFIRMING on first message
    is_policy_violation = metadata.get("_policy_violation", False)
    is_serious = severity in ("high",)  # high but not critical (critical already handled above)

    # Count exchanges in history
    is_first_message = not history or history.strip() == ""
    exchange_count = 0
    if not is_first_message:
        exchange_count = history.count("Employee:")

    if is_first_message:
        if is_policy_violation or is_serious:
            reason = metadata.get("_matched_policy", "") if is_policy_violation else f"high severity ({severity})"
            logger.info(f"[{trace_id}] Fast-track ({reason}) on first message → CONFIRMING")
            return {
                "severity": severity,
                "metadata": {
                    **metadata,
                    "_info_status": "CONFIRMING",
                    "_missing_info": [],
                }
            }
        logger.info(f"[{trace_id}] First message detected → forcing GATHERING")
    else:
        logger.info(f"[{trace_id}] Exchange count: {exchange_count}")

    # Check if we already asked for confirmation last time
    already_asked_confirmation = False
    if history and not is_first_message:
        history_lines = history.strip().split("\n")
        last_bot_lines = [l for l in history_lines if l.startswith("HR Assistant:")]
        if last_bot_lines:
            last_bot_msg = last_bot_lines[-1].lower()
            confirmation_phrases = [
                "anything else", "anything more", "something else",
                "more to add", "ready to", "shall i", "would you like to add",
                "want to add", "go ahead and", "take this forward",
                "properly addressed", "before i", "before we",
                "is there anything", "anything you'd like",
            ]
            already_asked_confirmation = any(p in last_bot_msg for p in confirmation_phrases)

    if already_asked_confirmation:
        logger.info(f"[{trace_id}] User confirmed after confirmation prompt → COMPLETE")
        return {
            "severity": severity,
            "metadata": {
                **metadata,
                "_info_status": "COMPLETE",
                "_missing_info": [],
            }
        }

    # Hard safeguard: after 3+ exchanges, force CONFIRMING (never loop forever)
    if exchange_count >= 3:
        logger.info(f"[{trace_id}] {exchange_count} exchanges reached → forcing CONFIRMING")
        return {
            "metadata": {
                **metadata,
                "_info_status": "CONFIRMING",
                "_missing_info": [],
            }
        }

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(InfoCompletenessResult)
        prompt = INFO_COMPLETENESS_PROMPT.format(
            conversation_history=history if history else "(This is the first message)",
            message=message,
        )
        result: InfoCompletenessResult = structured_llm.invoke(prompt)
        logger.info(f"[{trace_id}] Completeness: status={result.status}, missing={result.missing_info}")

        # Hard override: first message is ALWAYS GATHERING
        if is_first_message:
            final_status = "GATHERING"
            final_missing = result.missing_info
        elif result.status == "COMPLETE":
            # LLM says complete, but we haven't asked confirmation yet → CONFIRMING
            final_status = "CONFIRMING"
            final_missing = []
        else:
            final_status = result.status
            final_missing = result.missing_info

        return {
            "metadata": {
                **metadata,
                "_info_status": final_status,
                "_missing_info": final_missing,
            }
        }
    except Exception as e:
        logger.error(f"[{trace_id}] Error in completeness check: {e}")
        # On error, default to GATHERING for first message, COMPLETE for follow-ups
        status = "COMPLETE" if history else "GATHERING"
        return {
            "metadata": {
                **metadata,
                "_info_status": status,
                "_missing_info": [],
            }
        }


def ask_followup_node(state: HRState) -> dict:
    """Node: generate a natural follow-up question to gather more info."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Generating follow-up question")

    metadata = state.get("metadata", {})
    history = metadata.get("_complaint_history", "")
    message = state.get("message", "")
    missing = metadata.get("_missing_info", [])

    try:
        llm = get_llm()
        prompt = FOLLOWUP_PROMPT.format(
            conversation_history=history if history else "(First message)",
            message=message,
            missing_info=", ".join(missing) if missing else "general details",
        )
        ai_message = llm.invoke(prompt)
        logger.info(f"[{trace_id}] Follow-up generated ({len(ai_message.content)} chars)")
        return {"response": ai_message.content}

    except Exception as e:
        logger.error(f"[{trace_id}] Error generating follow-up: {e}")
        return {
            "response": (
                "Thank you for sharing that with me. I want to make sure I understand "
                "your situation fully so we can help you properly. Could you tell me "
                "a bit more about when this happened and who was involved?"
            )
        }


def ask_confirmation_node(state: HRState) -> dict:
    """Node: ask the employee to confirm before creating the ticket."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Asking for confirmation before ticket creation")

    metadata = state.get("metadata", {})
    history = metadata.get("_complaint_history", "")
    message = state.get("message", "")
    is_policy_violation = metadata.get("_policy_violation", False)
    policy_summary = metadata.get("_policy_summary", "")
    severity = state.get("severity", "medium")

    # Build extra context for the confirmation prompt
    policy_context = ""
    if is_policy_violation and policy_summary:
        policy_context = (
            f"\n\nIMPORTANT: This complaint matches a company policy violation — "
            f"{policy_summary}. Mention briefly that this falls under company policy "
            f"and will be treated with high priority."
        )
    elif severity in ("high", "critical"):
        policy_context = (
            f"\n\nIMPORTANT: This is a serious complaint (severity: {severity}). "
            f"Acknowledge the gravity and assure them it will be treated urgently."
        )

    try:
        llm = get_llm()
        prompt = CONFIRMATION_PROMPT.format(
            conversation_history=history if history else "(First message)",
            message=message,
        ) + policy_context
        ai_message = llm.invoke(prompt)
        logger.info(f"[{trace_id}] Confirmation question generated")
        return {"response": ai_message.content}

    except Exception as e:
        logger.error(f"[{trace_id}] Error generating confirmation: {e}")
        return {
            "response": (
                "I hear you, and what you've described is something we take very seriously. "
                "Is there anything else you'd like to add before I take this forward?"
            )
        }


def generate_summary_node(state: HRState) -> dict:
    """Node: generate a professional summary of the complaint for the ticket."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Generating complaint summary for ticket")

    metadata = state.get("metadata", {})
    history = metadata.get("_complaint_history", "")
    message = state.get("message", "")

    full_history = history
    if full_history:
        full_history += f"\nEmployee: {message}"
    else:
        full_history = f"Employee: {message}"

    try:
        llm = get_llm()
        prompt = TICKET_SUMMARY_PROMPT.format(conversation_history=full_history)
        ai_message = llm.invoke(prompt)
        summary = ai_message.content.strip()
        logger.info(f"[{trace_id}] Summary generated ({len(summary)} chars)")

        return {
            "metadata": {
                **metadata,
                "_ticket_summary": summary,
            }
        }
    except Exception as e:
        logger.error(f"[{trace_id}] Error generating summary: {e}")
        return {
            "metadata": {
                **metadata,
                "_ticket_summary": message,
            }
        }


def generate_warm_closing_node(state: HRState) -> dict:
    """Node: generate a warm, human closing response after ticket creation."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Generating warm closing message")

    try:
        llm = get_llm()
        prompt = WARM_CLOSING_PROMPT.format(
            complaint_type=state.get("complaint_type", "other"),
            emotion=state.get("emotion", "neutral"),
            severity=state.get("severity", "medium"),
        )
        ai_message = llm.invoke(prompt)
        logger.info(f"[{trace_id}] Warm closing generated")
        return {"response": ai_message.content}

    except Exception as e:
        logger.error(f"[{trace_id}] Error generating closing: {e}")
        return {
            "response": (
                "Thank you so much for trusting me with this. I want you to know "
                "that your concern is being taken seriously and someone from our HR "
                "team will personally reach out to you very soon. You're not alone "
                "in this — we're here to support you."
            )
        }


def escalate_node(state: HRState) -> dict:
    """Node: execute escalation — use the generated summary for the ticket."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Entering escalate_node")

    metadata = state.get("metadata", {})
    summary = metadata.get("_ticket_summary", state.get("message", ""))

    # Override the message temporarily with the summary for ticket description
    modified_state = {**state, "message": summary}

    try:
        return handle_escalation(modified_state)
    except Exception as e:
        logger.error(f"[{trace_id}] Error in escalate_node: {e}")
        return {"escalation_action": "log_only"}


def enrich_response_node(state: HRState) -> dict:
    """Node: append ticket notification to the response if a ticket was created."""
    trace_id = state.get("trace_id", "N/A")
    metadata = state.get("metadata", {})
    ticket_id = metadata.get("ticket_id", "")
    escalation_action = state.get("escalation_action", "")
    response = state.get("response", "")

    if ticket_id and escalation_action in ("create_ticket", "notify_hr"):
        severity = state.get("severity", "medium")
        severity_label = severity.upper()
        severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(severity, "🟡")
        ticket_notice = (
            f"\n\n---\n\n"
            f"### ✅ Your Complaint Has Been Registered\n\n"
            f"**Ticket ID:** `{ticket_id}`\n\n"
            f"**Priority:** {severity_emoji} {severity_label}\n\n"
            f"**Status:** 🔵 Open\n\n"
            f"> 💬 *An HR representative has been notified and will reach out to you shortly. "
            f"Your privacy and confidentiality are our top priority.*\n\n"
            f"📋 You can track your ticket status anytime from the **My Tickets** page."
        )
        response += ticket_notice
        logger.info(f"[{trace_id}] Enriched response with ticket notification: {ticket_id}")
        return {"response": response}

    return {}


def save_to_memory_node(state: HRState) -> dict:
    """Node: persist the full conversation context to memory."""
    trace_id = state.get("trace_id", "N/A")
    logger.info(f"[{trace_id}] Entering save_to_memory_node")
    try:
        store = get_memory_store()
        entry = ConversationEntry(
            user_id=state.get("user_id", "unknown"),
            message=state.get("message", ""),
            response=state.get("response", ""),
            intent=state.get("intent", ""),
            emotion=state.get("emotion", ""),
            severity=state.get("severity", ""),
            agent_used=state.get("agent_used", "complaint_agent"),
            trace_id=trace_id,
        )
        store.save_conversation(entry)
        logger.info(f"[{trace_id}] Conversation saved to memory")
        return {}
    except Exception as e:
        logger.error(f"[{trace_id}] Error in save_to_memory_node: {e}")
        return {}


# ---------------------------------------------------------------------------
# Conditional edges
# ---------------------------------------------------------------------------

def route_after_safety(state: HRState) -> str:
    """After safety check, load history."""
    return "load_history"


def route_after_completeness(state: HRState) -> str:
    """After completeness check, decide: gather more, confirm, or create ticket."""
    metadata = state.get("metadata", {})
    status = metadata.get("_info_status", "GATHERING")

    if status == "COMPLETE":
        return "generate_summary"
    if status == "CONFIRMING":
        return "ask_confirmation"
    return "ask_followup"


# ---------------------------------------------------------------------------
# Build the subgraph
# ---------------------------------------------------------------------------

def build_complaint_graph() -> StateGraph:
    """Construct and compile the Complaint Agent subgraph."""
    graph = StateGraph(HRState)

    graph.add_node("classify", classify_node)
    graph.add_node("safety_check", safety_check_node)
    graph.add_node("load_history", load_history_node)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("check_completeness", check_completeness_node)
    graph.add_node("ask_followup", ask_followup_node)
    graph.add_node("ask_confirmation", ask_confirmation_node)
    graph.add_node("generate_summary", generate_summary_node)
    graph.add_node("generate_warm_closing", generate_warm_closing_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("enrich_response", enrich_response_node)
    graph.add_node("save_to_memory", save_to_memory_node)

    graph.add_edge(START, "classify")
    graph.add_edge("classify", "safety_check")
    graph.add_conditional_edges("safety_check", route_after_safety)
    graph.add_edge("load_history", "policy_check")
    graph.add_edge("policy_check", "check_completeness")
    graph.add_conditional_edges("check_completeness", route_after_completeness)

    # GATHERING path: ask follow-up → save → end
    graph.add_edge("ask_followup", "save_to_memory")

    # CONFIRMING path: ask confirmation → save → end
    graph.add_edge("ask_confirmation", "save_to_memory")

    # COMPLETE path: summary → warm closing → escalate → enrich → save → end
    graph.add_edge("generate_summary", "generate_warm_closing")
    graph.add_edge("generate_warm_closing", "escalate")
    graph.add_edge("escalate", "enrich_response")
    graph.add_edge("enrich_response", "save_to_memory")

    graph.add_edge("save_to_memory", END)

    return graph.compile()
