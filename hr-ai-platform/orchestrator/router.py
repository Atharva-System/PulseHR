"""Intent router — LLM-based classification of user messages.

Uses a **dedicated low-temperature LLM** for deterministic classification
and includes few-shot examples so the model reliably distinguishes intents.
"""

from __future__ import annotations

from typing import Literal

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from pydantic import BaseModel, Field

from app.config import settings
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
# Structured output model
# ---------------------------------------------------------------------------

class IntentClassification(BaseModel):
    """Schema returned by the LLM for intent classification."""

    intent: str = Field(
        description=(
            "One of: employee_complaint, leave_request, payroll_query, "
            "policy_question, general_query"
        )
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0"
    )


# ---------------------------------------------------------------------------
# Dedicated low-temperature router LLM (singleton)
# ---------------------------------------------------------------------------
_router_llm: ChatNVIDIA | None = None


def _get_router_llm() -> ChatNVIDIA:
    """Return a ChatNVIDIA instance tuned for deterministic classification."""
    global _router_llm
    if _router_llm is None:
        _router_llm = ChatNVIDIA(
            model=settings.model_name,
            api_key=settings.nvidia_api_key,
            temperature=0.1,          # near-deterministic for classification
            top_p=0.9,
            max_tokens=256,            # classification needs very few tokens
        )
    return _router_llm


# ---------------------------------------------------------------------------
# Prompt  (with few-shot examples for reliable classification)
# ---------------------------------------------------------------------------

INTENT_PROMPT = """\
You are an expert HR intent classifier. Your ONLY job is to read the employee's \
message and return the single best intent category.

=== CATEGORIES ===
1. employee_complaint  – The employee is filing a complaint, reporting misconduct, \
harassment, bullying, unfair treatment, discrimination, a hostile work environment, \
or expressing dissatisfaction about a person/policy/working condition. Also applies \
when the recent history shows an ongoing complaint conversation and the employee is \
replying with follow-up details or confirmations.
2. leave_request       – Anything about applying for leave, checking leave balance, \
vacation days, sick leave, time off, PTO, FMLA, or absence.
3. payroll_query       – Anything about salary, payslip, pay stub, deductions, \
bonuses, compensation, tax, or wages.
4. policy_question     – The employee is asking about company policies, rules, \
guidelines, procedures, employee handbook, work-from-home policy, dress code, \
probation period, notice period, or any official HR policy.
5. general_query       – Greetings, small talk, thank-you messages, positive \
feedback about resolved tickets, or anything that does NOT fit categories 1–4.

=== FEW-SHOT EXAMPLES ===
Employee: "I want to file a complaint against my manager for constant criticism."
→ intent: employee_complaint, confidence: 0.98

Employee: "What is our leave policy?"
→ intent: policy_question, confidence: 0.97

Employee: "How many vacation days do I have left?"
→ intent: leave_request, confidence: 0.96

Employee: "I want to apply for sick leave next Monday."
→ intent: leave_request, confidence: 0.97

Employee: "Can I see my latest payslip?"
→ intent: payroll_query, confidence: 0.97

Employee: "What is the work from home policy?"
→ intent: policy_question, confidence: 0.97

Employee: "What's the company policy on probation period?"
→ intent: policy_question, confidence: 0.97

Employee: "My manager has been harassing me and I want to report it."
→ intent: employee_complaint, confidence: 0.99

Employee: "Hello, how are you?"
→ intent: general_query, confidence: 0.95

Employee: "Thanks, that's helpful!"
→ intent: general_query, confidence: 0.93

Employee: "What are the working hours policy?"
→ intent: policy_question, confidence: 0.96

Employee: "How much is my salary this month?"
→ intent: payroll_query, confidence: 0.96

Employee: "I'd like to take 3 days off next week."
→ intent: leave_request, confidence: 0.97

=== CONTEXT ===
RECENT CONVERSATION HISTORY:
{conversation_history}

TICKET CONTEXT:
{ticket_context}

CURRENT EMPLOYEE MESSAGE:
{message}

=== RULES ===
1. If the conversation history shows an ongoing complaint and the employee's \
current message is a short reply or confirmation, classify as employee_complaint.
2. If the employee has a resolved ticket and says they are NOT satisfied, \
classify as employee_complaint.
3. If the last assistant message shows a ticket was ALREADY CREATED (contains \
"Complaint Has Been Registered", "Ticket ID:", "TKT-"), classify as general_query \
UNLESS the employee is raising a completely NEW complaint topic.
4. When in doubt between policy_question and general_query, prefer policy_question \
if the message mentions any policy, rule, guideline, or procedure.
5. When in doubt between leave_request and policy_question for leave-related \
messages, classify as policy_question if they are asking ABOUT the policy, and \
leave_request if they want to TAKE leave or CHECK their balance.

Return the intent and your confidence (0.0 – 1.0).
"""


# ---------------------------------------------------------------------------
# Router function (graph node)
# ---------------------------------------------------------------------------

def classify_intent(state: HRState) -> dict:
    """Classify the user's intent using a low-temperature LLM.

    Returns dict with ``intent`` and ``confidence``.
    """
    trace_id = state.get("trace_id", "N/A")
    message = state.get("message", "")

    logger.info(f"[{trace_id}] Classifying intent for message: {message[:80]}...")

    try:
        # Use dedicated low-temperature LLM for deterministic classification
        router_llm = _get_router_llm()
        structured_llm = router_llm.with_structured_output(IntentClassification)

        # Build conversation history string for context
        history_parts = []
        for entry in state.get("conversation_history", []):
            history_parts.append(f"Employee: {entry.get('content', '')}")
            history_parts.append(f"HR Assistant: {entry.get('content2', '')}")
        history_str = "\n".join(history_parts) if history_parts else "(No prior conversation)"

        # ---------- Programmatic guard: ticket already created ----------
        # If the last bot response contains ticket creation markers,
        # and the new message is short/generic, skip complaint entirely.
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
            ticket_parts.append(f"- OPEN ticket {t['ticket_id']}: {t.get('title','')} (severity: {t.get('severity','')})")
        for t in tc.get("resolved_tickets", []):
            fb_info = f", rating: {t['rating']}/5" if t.get("rating") else ", no feedback yet"
            ticket_parts.append(f"- RESOLVED ticket {t['ticket_id']}: {t.get('title','')}{fb_info}")
        for t in tc.get("closed_tickets", []):
            fb_info = f", rating: {t['rating']}/5" if t.get("rating") else ""
            ticket_parts.append(f"- CLOSED ticket {t['ticket_id']}: {t.get('title','')}{fb_info}")
        ticket_str = "\n".join(ticket_parts) if ticket_parts else "(No tickets)"

        prompt = INTENT_PROMPT.format(
            message=message,
            conversation_history=history_str,
            ticket_context=ticket_str,
        )
        result: IntentClassification = structured_llm.invoke(prompt)

        # Validate the returned intent is one of the known categories
        if result.intent not in VALID_INTENTS:
            logger.warning(
                f"[{trace_id}] LLM returned unknown intent '{result.intent}', "
                f"falling back to general_query"
            )
            return {"intent": "general_query", "confidence": 0.5}

        logger.info(
            f"[{trace_id}] Intent detected: {result.intent} "
            f"(confidence: {result.confidence:.2f})"
        )
        return {
            "intent": result.intent,
            "confidence": result.confidence,
        }

    except Exception as e:
        logger.error(f"[{trace_id}] Error in classify_intent: {e}")
        return {
            "intent": "general_query",
            "confidence": 0.0,
        }
