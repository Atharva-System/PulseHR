"""Intent router — LLM-based classification of user messages.

Uses a plain LLM call with JSON parsing (no with_structured_output) for
maximum compatibility across all deployment environments.
"""

from __future__ import annotations

import json
import re
import traceback

from app.dependencies import get_llm, get_llm_for_agent
from orchestrator.state import HRState
from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Valid intents (single source of truth)
# ---------------------------------------------------------------------------
VALID_INTENTS = {
    "employee_complaint",
    "leave_request",
    "payroll_query",
    "policy_question",
    "general_query",
}


# ---------------------------------------------------------------------------
# Prompt  (with few-shot examples — asks LLM to return plain JSON)
# ---------------------------------------------------------------------------

INTENT_PROMPT = """\
You are an expert HR intent classifier. Read the employee's message and return \
ONLY a JSON object with "intent" and "confidence". No other text.

CATEGORIES:
- employee_complaint: filing a complaint, reporting misconduct, harassment, \
bullying, unfair treatment, discrimination, hostile work environment, or \
dissatisfaction about a person/policy/working condition. Also for follow-up \
replies in an ongoing complaint conversation.
- leave_request: applying for leave, checking leave balance, vacation days, \
sick leave, time off, PTO, FMLA, or absence.
- payroll_query: salary, payslip, pay stub, deductions, bonuses, compensation, \
tax, or wages.
- policy_question: asking about company policies, rules, guidelines, procedures, \
employee handbook, work-from-home policy, dress code, probation, notice period, \
or any official HR policy.
- general_query: greetings, small talk, thank-you messages, positive feedback, \
or anything that does NOT fit above categories.

EXAMPLES:
Employee: "I want to file a complaint against my manager"
{{"intent": "employee_complaint", "confidence": 0.98}}

Employee: "What is our leave policy?"
{{"intent": "policy_question", "confidence": 0.97}}

Employee: "How many vacation days do I have left?"
{{"intent": "leave_request", "confidence": 0.96}}

Employee: "I want to apply for sick leave next Monday"
{{"intent": "leave_request", "confidence": 0.97}}

Employee: "Can I see my latest payslip?"
{{"intent": "payroll_query", "confidence": 0.97}}

Employee: "What is the work from home policy?"
{{"intent": "policy_question", "confidence": 0.97}}

Employee: "What's the company policy on probation period?"
{{"intent": "policy_question", "confidence": 0.97}}

Employee: "My manager has been harassing me"
{{"intent": "employee_complaint", "confidence": 0.99}}

Employee: "Hello, how are you?"
{{"intent": "general_query", "confidence": 0.95}}

Employee: "Thanks, that's helpful!"
{{"intent": "general_query", "confidence": 0.93}}

Employee: "What are the working hours?"
{{"intent": "policy_question", "confidence": 0.96}}

Employee: "How much is my salary this month?"
{{"intent": "payroll_query", "confidence": 0.96}}

Employee: "I'd like to take 3 days off next week"
{{"intent": "leave_request", "confidence": 0.97}}

Employee: "can you tell me about leave policy"
{{"intent": "policy_question", "confidence": 0.97}}

CONTEXT:
History: {conversation_history}
Tickets: {ticket_context}

CURRENT MESSAGE: {message}

RULES:
1. Ongoing complaint + short reply → employee_complaint
2. Resolved ticket + NOT satisfied → employee_complaint
3. Ticket ALREADY CREATED + greeting/short reply → general_query
4. Mentions policy/rule/guideline → prefer policy_question over general_query
5. Asking ABOUT leave policy → policy_question; wanting to TAKE leave → leave_request

Respond with ONLY the JSON object, nothing else:
"""


# ---------------------------------------------------------------------------
# JSON parser — extracts intent from plain LLM text response
# ---------------------------------------------------------------------------

def _parse_intent_response(text: str) -> tuple[str, float]:
    """Extract intent and confidence from LLM plain-text response.

    Tries JSON parsing first, then regex fallback.
    Returns (intent, confidence).
    """
    # Try to find JSON in the response
    json_match = re.search(r'\{[^}]+\}', text)
    if json_match:
        try:
            data = json.loads(json_match.group())
            intent = data.get("intent", "general_query")
            confidence = float(data.get("confidence", 0.9))
            return intent, confidence
        except (json.JSONDecodeError, ValueError):
            pass

    # Regex fallback: look for intent value in text
    for valid in VALID_INTENTS:
        if valid in text.lower():
            return valid, 0.85

    return "general_query", 0.5


# ---------------------------------------------------------------------------
# Router function (graph node)
# ---------------------------------------------------------------------------

def classify_intent(state: HRState) -> dict:
    """Classify the user's intent using a plain LLM call + JSON parsing.

    Returns dict with ``intent`` and ``confidence``.
    """
    trace_id = state.get("trace_id", "N/A")
    message = state.get("message", "")

    logger.info(f"[{trace_id}] Classifying intent for message: {message[:80]}...")

    try:
        llm = get_llm()

        # Build conversation history string for context
        history_parts = []
        for entry in state.get("conversation_history", []):
            history_parts.append(f"Employee: {entry.get('content', '')}")
            history_parts.append(f"HR Assistant: {entry.get('content2', '')}")
        history_str = "\n".join(history_parts) if history_parts else "(none)"

        # ---------- Programmatic guard: ticket already created ----------
        last_bot_msg = ""
        for entry in reversed(state.get("conversation_history", [])):
            if entry.get("content2"):
                last_bot_msg = entry["content2"]
                break

        _ticket_markers = [
            "Complaint Has Been Registered",
            "Ticket ID:",
            "TKT-",
            "ticket has been registered",
            "Re-opened & Escalated",
        ]
        ticket_just_created = any(m in last_bot_msg for m in _ticket_markers)

        if ticket_just_created:
            word_count = len(message.split())
            _greetings = {
                "hi", "hello", "hey", "ok", "okay", "thanks", "thank you",
                "no", "yes", "bye", "sure", "fine", "good", "great",
                "hmm", "hm", "alright", "cool", "yep", "nope", "no thanks",
            }
            if message.strip().lower() in _greetings or word_count <= 8:
                logger.info(
                    f"[{trace_id}] Ticket just created + short follow-up → general_query"
                )
                return {"intent": "general_query", "confidence": 0.95}

        # Build ticket context string
        tc = state.get("ticket_context", {})
        ticket_parts = []
        for t in tc.get("open_tickets", []):
            ticket_parts.append(f"OPEN {t['ticket_id']}: {t.get('title','')}")
        for t in tc.get("resolved_tickets", []):
            ticket_parts.append(f"RESOLVED {t['ticket_id']}: {t.get('title','')}")
        for t in tc.get("closed_tickets", []):
            ticket_parts.append(f"CLOSED {t['ticket_id']}: {t.get('title','')}")
        ticket_str = ", ".join(ticket_parts) if ticket_parts else "(none)"

        prompt = INTENT_PROMPT.format(
            message=message,
            conversation_history=history_str,
            ticket_context=ticket_str,
        )

        # Plain LLM call — no with_structured_output, maximum compatibility
        ai_message = llm.invoke(prompt)
        raw_text = ai_message.content.strip()
        logger.info(f"[{trace_id}] Raw LLM response: {raw_text[:120]}")

        intent, confidence = _parse_intent_response(raw_text)

        # Validate
        if intent not in VALID_INTENTS:
            logger.warning(
                f"[{trace_id}] LLM returned unknown intent '{intent}', "
                f"falling back to general_query"
            )
            return {"intent": "general_query", "confidence": 0.5}

        logger.info(
            f"[{trace_id}] Intent detected: {intent} "
            f"(confidence: {confidence:.2f})"
        )
        return {"intent": intent, "confidence": confidence}

    except Exception as e:
        logger.error(f"[{trace_id}] Error in classify_intent: {e}")
        logger.error(f"[{trace_id}] Traceback: {traceback.format_exc()}")
        return {
            "intent": "general_query",
            "confidence": 0.0,
        }
