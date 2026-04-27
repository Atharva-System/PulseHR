"""Complaint Agent — LangGraph subgraph with conversational info gathering.

Graph flow:
    ticket_check →
        if DISSATISFIED: handle_dissatisfaction → save_to_memory
        if NEW_COMPLAINT or NO_TICKETS:
            classify → safety_check → load_history → check_completeness →
                if GATHERING: ask_followup → save_to_memory
                if COMPLETE:  generate_summary → escalate → enrich_response → save_to_memory
"""

import re
from langgraph.graph import StateGraph, START, END

from app.dependencies import get_llm, get_llm_for_agent, get_memory_store
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
    DISSATISFACTION_CHECK_PROMPT,
    DISSATISFACTION_RESPONSE_PROMPT,
)
from agents.complaint.schemas import (
    SafetyCheckResult,
    InfoCompletenessResult,
    PolicyViolationResult,
    DissatisfactionCheckResult,
)
from agents.policy.tools import search_policies
from memory.schemas import ConversationEntry
from orchestrator.state import HRState
from db.connection import get_db_session
from db.models import ConversationModel, TicketModel
from utils.context import build_compact_history, strip_ticket_notice
from utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_recent_complaint_history(user_id: str, thread_id: str, limit: int = 8) -> str:
    """Load recent complaint conversations for the active complaint thread."""
    session = get_db_session()
    try:
        q = (
            session.query(ConversationModel)
            .filter(
                ConversationModel.user_id == user_id,
                ConversationModel.intent == "employee_complaint",
            )
        )
        if thread_id:
            q = q.filter(ConversationModel.thread_id == thread_id)

        rows = q.order_by(ConversationModel.timestamp.desc()).limit(limit).all()
        if not rows:
            return ""

        rows.reverse()  # chronological order
        entries = [
            {"content": r.message, "content2": strip_ticket_notice(r.response or "")}
            for r in rows
        ]
        return build_compact_history(entries, max_turns=limit, max_chars_per_message=260)
    finally:
        session.close()


def _load_max_severity(user_id: str, thread_id: str) -> str:
    """Load the highest severity from recent complaint conversations in a thread.

    This prevents short follow-up messages like 'no' or 'ok' from
    downgrading the severity that was set during the original complaint.
    """
    severity_order = ["low", "medium", "high", "critical"]
    session = get_db_session()
    try:
        q = (
            session.query(ConversationModel.severity)
            .filter(
                ConversationModel.user_id == user_id,
                ConversationModel.intent == "employee_complaint",
                ConversationModel.severity != "",
                ConversationModel.severity.isnot(None),
            )
        )
        if thread_id:
            q = q.filter(ConversationModel.thread_id == thread_id)

        rows = q.order_by(ConversationModel.timestamp.desc()).limit(10).all()
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


def _extract_name(text: str) -> str:
    patterns = [
        r"\b(?:manager|colleague|supervisor|team lead|lead|hr|director)\s+([A-Z][a-z]+)\b",
        r"\b([A-Z][a-z]+)\s+(?:from|in|of)\s+([A-Za-z]+)\b",
        r"\b(?:about|named|called)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        if len(match.groups()) == 2:
            return f"{match.group(1)} {match.group(2)}".strip()
        return match.group(1).strip()
    return ""


def _has_time_reference(text: str) -> bool:
    time_patterns = (
        r"\b(today|yesterday|tonight|this morning|this evening)\b",
        r"\b(last|this|next)\s+(week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b\d{1,2}[:/.-]\d{1,2}(?:[:/.-]\d{2,4})?\b",
        r"\b\d{1,2}\s*(?:am|pm)\b",
        r"\b(always|often|daily|weekly|repeatedly|every day|every week)\b",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in time_patterns)


def _has_incident_detail(text: str) -> bool:
    keywords = (
        "harass", "threat", "shout", "yell", "insult", "touch", "bully",
        "discrimin", "humiliat", "retaliat", "abuse", "misbehav", "scream",
    )
    normalized = " ".join(text.split())
    return len(normalized.split()) >= 6 or any(keyword in normalized.lower() for keyword in keywords)


def _required_missing_info(history: str, message: str) -> list[str]:
    combined = "\n".join(part for part in (history, message) if part).strip()
    missing: list[str] = []
    if not _extract_name(combined):
        missing.append("person's name")
    if not _has_incident_detail(combined):
        missing.append("what happened")
    if not _has_time_reference(combined):
        missing.append("when it happened")
    return missing


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
        llm = get_llm_for_agent("complaint_agent")
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
    thread_id = state.get("thread_id", "")
    logger.info(f"[{trace_id}] Loading complaint history for {user_id}")

    history = _load_recent_complaint_history(user_id, thread_id)

    # Also load the highest severity from previous conversation turns
    # so short follow-up messages ("no", "ok") don't downgrade it
    stored_severity = _load_max_severity(user_id, thread_id)

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

        llm = get_llm_for_agent("complaint_agent")
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

    # Count exchanges in history
    is_first_message = not history or history.strip() == ""
    exchange_count = 0
    if not is_first_message:
        exchange_count = history.count("Employee:")

    if is_first_message:
        logger.info(f"[{trace_id}] First message detected → forcing GATHERING")
    else:
        logger.info(f"[{trace_id}] Exchange count: {exchange_count}")

    rule_missing = _required_missing_info(history, message)

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
        if rule_missing:
            logger.info(f"[{trace_id}] Confirmation reply received but required info still missing")
            return {
                "severity": severity,
                "metadata": {
                    **metadata,
                    "_info_status": "GATHERING",
                    "_missing_info": rule_missing,
                }
            }
        logger.info(f"[{trace_id}] User confirmed after confirmation prompt → COMPLETE")
        return {
            "severity": severity,
            "metadata": {
                **metadata,
                "_info_status": "COMPLETE",
                "_missing_info": [],
            }
        }

    # Hard safeguard: after enough exchanges, force CONFIRMING (never loop forever)
    # Give at least 3 exchanges for all severities so the bot has time to ask
    # for the person's name, what happened, and when.
    max_exchanges = 3 if severity in ("critical", "high") else 4
    if exchange_count >= max_exchanges:
        if rule_missing:
            logger.info(f"[{trace_id}] Exchange cap reached but required info still missing: {rule_missing}")
            return {
                "severity": severity,
                "metadata": {
                    **metadata,
                    "_info_status": "GATHERING",
                    "_missing_info": rule_missing,
                }
            }
        logger.info(f"[{trace_id}] {exchange_count} exchanges reached (max={max_exchanges}) → forcing CONFIRMING")
        return {
            "severity": severity,
            "metadata": {
                **metadata,
                "_info_status": "CONFIRMING",
                "_missing_info": [],
            }
        }

    try:
        llm = get_llm_for_agent("complaint_agent")
        structured_llm = llm.with_structured_output(InfoCompletenessResult)
        prompt = INFO_COMPLETENESS_PROMPT.format(
            conversation_history=history if history else "(This is the first message)",
            message=message,
        )
        result: InfoCompletenessResult = structured_llm.invoke(prompt)
        logger.info(f"[{trace_id}] Completeness: status={result.status}, missing={result.missing_info}")
        merged_missing = list(dict.fromkeys([*rule_missing, *result.missing_info]))

        # Hard override: first message is ALWAYS GATHERING
        if is_first_message:
            final_status = "GATHERING"
            final_missing = merged_missing
        elif merged_missing:
            final_status = "GATHERING"
            final_missing = merged_missing
        elif result.status == "COMPLETE":
            # LLM says complete, but we haven't asked confirmation yet → CONFIRMING
            final_status = "CONFIRMING"
            final_missing = []
        else:
            final_status = result.status
            final_missing = merged_missing

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
    severity = state.get("severity", "medium")

    try:
        llm = get_llm_for_agent("complaint_agent")
        prompt = FOLLOWUP_PROMPT.format(
            conversation_history=history if history else "(First message)",
            message=message,
            missing_info=", ".join(missing) if missing else "general details",
            severity=severity,
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
        llm = get_llm_for_agent("complaint_agent")
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
    """Node: generate a professional summary of the complaint for the ticket.

    Also extracts the complaint_target (who the complaint is about).
    """
    import json as _json

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
        llm = get_llm_for_agent("complaint_agent")
        prompt = TICKET_SUMMARY_PROMPT.format(conversation_history=full_history)
        ai_message = llm.invoke(prompt)
        raw_text = ai_message.content.strip()
        logger.info(f"[{trace_id}] Summary raw response ({len(raw_text)} chars)")

        # Try to parse JSON; fall back to raw text
        summary = raw_text
        complaint_target = ""
        try:
            # Strip markdown fences if present
            cleaned = raw_text
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            # Also try to find JSON object within the text
            import re as _re
            json_match = _re.search(r'\{[^{}]*"summary"[^{}]*\}', cleaned, _re.DOTALL)
            if json_match:
                cleaned = json_match.group(0)
            parsed = _json.loads(cleaned.strip())
            summary = parsed.get("summary", raw_text)
            complaint_target = parsed.get("complaint_target", "")
        except (_json.JSONDecodeError, AttributeError):
            logger.warning(f"[{trace_id}] Could not parse summary JSON, using raw text")

        # Fallback: if complaint_target is empty or just a role, try to extract
        # the name from conversation history using simple heuristics
        if not complaint_target or complaint_target.lower() in (
            "manager", "colleague", "hr", "hr rep", "supervisor", "team lead",
        ):
            import re as _re
            # Look for names in employee messages from the full history
            # Pattern: capitalize words that look like names (after context clues)
            for pattern in [
                r"(?:name is|named|called|it'?s|about|from)\s+([A-Z][a-z]+(?:\s+(?:from|in|of)\s+\w+)?)",
                r"([A-Z][a-z]{2,})\s+(?:from|in|of)\s+([A-Za-z]+)",
            ]:
                match = _re.search(pattern, full_history)
                if match:
                    extracted = match.group(0)
                    # Clean up the extracted text
                    for prefix in ["name is ", "named ", "called ", "it's ", "about ", "from "]:
                        if extracted.lower().startswith(prefix):
                            extracted = extracted[len(prefix):]
                    complaint_target = extracted.strip()
                    logger.info(f"[{trace_id}] Fallback extracted complaint_target: {complaint_target}")
                    break

        # --- Auto-escalate if complaint is about HR staff ---
        from utils.privacy import is_complaint_about_hr
        privacy_override = {}
        if is_complaint_about_hr(complaint_target):
            current_privacy = state.get("privacy_mode", "identified")
            if current_privacy == "identified":
                logger.info(
                    f"[{trace_id}] Complaint target '{complaint_target}' is HR staff "
                    f"— auto-upgrading privacy from '{current_privacy}' to 'confidential'"
                )
                privacy_override = {
                    "privacy_mode": "confidential",
                    "metadata": {
                        **metadata,
                        "_ticket_summary": summary,
                        "_hr_auto_escalated": True,
                    },
                }

        # NOTE: For HR-targeted complaints, admin notification now happens in
        # handle_escalation() AFTER the ticket is created, so ticket_id is included.
        if is_complaint_about_hr(complaint_target):
            logger.info(f"[{trace_id}] HR-targeted complaint detected — admin will be notified during escalation")

        result = {
            "complaint_target": complaint_target,
            "metadata": {
                **metadata,
                "_ticket_summary": summary,
            },
        }
        # Merge in any privacy override
        if privacy_override:
            result.update(privacy_override)
        return result

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
        llm = get_llm_for_agent("complaint_agent")
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
    privacy_mode = state.get("privacy_mode", "identified")

    if ticket_id and escalation_action in ("create_ticket", "notify_hr", "escalate_to_admin"):
        severity = state.get("severity", "medium")
        severity_label = severity.upper()
        severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(severity, "🟡")
        complaint_target = state.get("complaint_target", "")
        hr_auto_escalated = metadata.get("_hr_auto_escalated", False)
        privacy_note = ""
        if hr_auto_escalated:
            privacy_note = (
                "\n\n🛡️ Since your complaint involves HR staff, we've automatically "
                "upgraded your privacy to **confidential mode**. Your identity will be "
                "hidden from HR and only visible to higher authority."
            )
        elif privacy_mode == "confidential":
            privacy_note = (
                "\n\n🔒 Your identity will be hidden from standard HR views and "
                "only visible to higher authority when needed."
            )
        elif privacy_mode == "anonymous":
            privacy_note = (
                "\n\n🕶️ Your ticket will be filed in anonymous mode so your name is "
                "not shown in HR review screens."
            )
        target_line = ""
        if complaint_target:
            target_line = f"**Complaint About:** {complaint_target}\n\n"
        ticket_notice = (
            f"\n\n---\n\n"
            f"### ✅ Your Complaint Has Been Registered\n\n"
            f"**Ticket ID:** `{ticket_id}`\n\n"
            f"{target_line}"
            f"**Priority:** {severity_emoji} {severity_label}\n\n"
            f"**Status:** 🔵 Open\n\n"
            f"> 💬 *An HR representative has been notified and will reach out to you shortly. "
            f"Your privacy and confidentiality are our top priority.*"
            f"{privacy_note}\n\n"
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
            privacy_mode=state.get("privacy_mode", "identified"),
            thread_id=state.get("thread_id", ""),
            trace_id=trace_id,
        )
        saved = store.save_conversation(entry)
        logger.info(f"[{trace_id}] Conversation saved to memory")
        return {
            "metadata": {
                **state.get("metadata", {}),
                "memory_persisted": bool(saved),
            }
        }
    except Exception as e:
        logger.error(f"[{trace_id}] Error in save_to_memory_node: {e}")
        return {}


# ---------------------------------------------------------------------------
# Ticket-aware nodes
# ---------------------------------------------------------------------------

def ticket_check_node(state: HRState) -> dict:
    """Node: check if the employee is referring to an existing ticket.

    Determines if this is dissatisfaction with a resolved ticket, or a new complaint.
    Also guards against duplicate ticket creation when a ticket was just created
    in the same conversation.
    """
    trace_id = state.get("trace_id", "N/A")
    tc = state.get("ticket_context", {})
    message = state.get("message", "")

    # ----- Guard: ticket was already created in this conversation -----
    _ticket_markers = [
        "Complaint Has Been Registered",
        "Ticket ID:",
        "TKT-",
        "ticket has been registered",
        "Re-opened & Escalated",
    ]
    for entry in reversed(state.get("conversation_history", [])):
        bot_msg = entry.get("content2", "")
        if any(m in bot_msg for m in _ticket_markers):
            logger.info(
                f"[{trace_id}] Ticket already created in conversation → TICKET_EXISTS"
            )
            return {
                "metadata": {
                    **state.get("metadata", {}),
                    "_ticket_check": "TICKET_EXISTS",
                },
                "response": (
                    "Your complaint has already been registered and our HR team "
                    "is actively looking into it. You can track your ticket status "
                    "anytime from the **My Tickets** page.\n\n"
                    "Is there anything else I can help you with?"
                ),
                "agent_used": "complaint_agent",
            }

    # If no tickets exist at all, skip straight to normal complaint flow
    has_any_tickets = (
        tc.get("open_tickets")
        or tc.get("resolved_tickets")
        or tc.get("closed_tickets")
    )
    if not has_any_tickets:
        logger.info(f"[{trace_id}] No tickets found → normal complaint flow")
        return {"metadata": {**state.get("metadata", {}), "_ticket_check": "NEW_COMPLAINT"}}

    logger.info(f"[{trace_id}] Checking ticket context for dissatisfaction")

    try:
        llm = get_llm_for_agent("complaint_agent")
        structured_llm = llm.with_structured_output(DissatisfactionCheckResult)

        # Build ticket context string
        ticket_parts = []
        for t in tc.get("open_tickets", []):
            ticket_parts.append(f"- OPEN: {t['ticket_id']} — {t.get('title','')}")
        for t in tc.get("resolved_tickets", []):
            fb = f", feedback: {t.get('rating','')}/5" if t.get("rating") else ", no feedback"
            ticket_parts.append(f"- RESOLVED: {t['ticket_id']} — {t.get('title','')}{fb}")
        for t in tc.get("closed_tickets", []):
            fb = f", rating: {t.get('rating','')}/5" if t.get("rating") else ""
            ticket_parts.append(f"- CLOSED: {t['ticket_id']} — {t.get('title','')}{fb}")
        ticket_str = "\n".join(ticket_parts)

        # Build conversation history
        history_parts = []
        for entry in state.get("conversation_history", []):
            history_parts.append(f"Employee: {entry.get('content', '')}")
            history_parts.append(f"HR Assistant: {entry.get('content2', '')}")
        history_str = "\n".join(history_parts) if history_parts else "(No history)"

        prompt = DISSATISFACTION_CHECK_PROMPT.format(
            ticket_context=ticket_str,
            conversation_history=history_str,
            message=message,
        )
        result: DissatisfactionCheckResult = structured_llm.invoke(prompt)
        logger.info(
            f"[{trace_id}] Ticket check: dissatisfied={result.is_dissatisfied}, "
            f"new_complaint={result.is_new_complaint}, ticket={result.related_ticket_id}"
        )

        metadata = state.get("metadata", {})

        if result.is_dissatisfied and result.related_ticket_id:
            metadata["_ticket_check"] = "DISSATISFIED"
            metadata["_dissatisfied_ticket_id"] = result.related_ticket_id
            return {"metadata": metadata}

        metadata["_ticket_check"] = "NEW_COMPLAINT"
        return {"metadata": metadata}

    except Exception as e:
        logger.error(f"[{trace_id}] Error in ticket_check_node: {e}")
        return {"metadata": {**state.get("metadata", {}), "_ticket_check": "NEW_COMPLAINT"}}


def handle_dissatisfaction_node(state: HRState) -> dict:
    """Node: handle employee dissatisfaction with a resolved/closed ticket.

    - Generates an empathetic response
    - Re-opens the ticket
    - Escalates to higher authority via email
    """
    trace_id = state.get("trace_id", "N/A")
    metadata = state.get("metadata", {})
    ticket_id = metadata.get("_dissatisfied_ticket_id", "")
    message = state.get("message", "")
    user_id = state.get("user_id", "unknown")

    logger.info(f"[{trace_id}] Handling dissatisfaction for ticket {ticket_id}")

    # Load ticket details and re-open
    ticket_title = ""
    ticket_status = ""
    ticket_severity = ""
    if ticket_id:
        session = get_db_session()
        try:
            ticket = session.query(TicketModel).filter_by(ticket_id=ticket_id).first()
            if ticket:
                ticket_title = ticket.title or ""
                ticket_status = ticket.status or ""
                ticket_severity = ticket.severity or "medium"

                # Re-open the ticket
                ticket.status = "open"
                session.commit()
                logger.info(f"[{trace_id}] Ticket {ticket_id} re-opened due to dissatisfaction")
        except Exception as e:
            logger.error(f"[{trace_id}] Error re-opening ticket: {e}")
        finally:
            session.close()

    # Generate empathetic response via LLM
    try:
        llm = get_llm_for_agent("complaint_agent")
        prompt = DISSATISFACTION_RESPONSE_PROMPT.format(
            ticket_id=ticket_id,
            ticket_title=ticket_title,
            ticket_status=ticket_status,
            message=message,
        )
        ai_message = llm.invoke(prompt)
        response_text = ai_message.content
    except Exception as e:
        logger.error(f"[{trace_id}] Error generating dissatisfaction response: {e}")
        response_text = (
            "I understand your concern, and I'm sorry to hear the issue wasn't resolved "
            "to your satisfaction. I'm escalating this to senior management right away "
            "for a thorough review. Could you tell me what specifically hasn't been addressed?"
        )

    # Append re-escalation notice
    severity_emoji = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}.get(
        ticket_severity, "🟡"
    )
    response_text += (
        f"\n\n---\n\n"
        f"### 🔄 Ticket Re-opened & Escalated\n\n"
        f"**Ticket ID:** `{ticket_id}`\n\n"
        f"**Priority:** {severity_emoji} {ticket_severity.upper()}\n\n"
        f"**Status:** 🔵 Re-opened\n\n"
        f"> ⬆️ *This has been escalated to senior management for immediate review. "
        f"You will be contacted directly.*"
    )

    # Email higher authority about dissatisfaction
    try:
        from escalation.notifier import notify_authority
        notify_authority(
            f"DISSATISFACTION RE-ESCALATION — Ticket {ticket_id}\n\n"
            f"Employee ({user_id}) is dissatisfied with the resolution of ticket {ticket_id}.\n"
            f"Original complaint: {ticket_title}\n"
            f"Employee's message: {message}\n\n"
            f"The ticket has been re-opened automatically. Please review urgently.",
            severity=ticket_severity or "high",
            ticket_id=ticket_id,
        )
        logger.info(f"[{trace_id}] Dissatisfaction escalation email sent to authority")
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to send dissatisfaction escalation email: {e}")

    return {
        "response": response_text,
        "agent_used": "complaint_agent",
        "escalation_action": "notify_authority",
    }


# ---------------------------------------------------------------------------
# Conditional edges
# ---------------------------------------------------------------------------

def route_after_safety(state: HRState) -> str:
    """After safety check, load history."""
    return "load_history"


def route_after_ticket_check(state: HRState) -> str:
    """After ticket check, either handle dissatisfaction, exit early, or proceed."""
    metadata = state.get("metadata", {})
    check_result = metadata.get("_ticket_check", "NEW_COMPLAINT")

    if check_result == "TICKET_EXISTS":
        return "save_to_memory"
    if check_result == "DISSATISFIED":
        return "handle_dissatisfaction"
    return "classify"


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

    # Ticket-aware nodes
    graph.add_node("ticket_check", ticket_check_node)
    graph.add_node("handle_dissatisfaction", handle_dissatisfaction_node)

    # Original nodes
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

    # --- Entry: ticket check first ---
    graph.add_edge(START, "ticket_check")
    graph.add_conditional_edges("ticket_check", route_after_ticket_check)

    # Dissatisfaction path → save → end
    graph.add_edge("handle_dissatisfaction", "save_to_memory")

    # Normal complaint flow
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
