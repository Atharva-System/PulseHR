"""Intent router — LLM-based classification of user messages."""

from pydantic import BaseModel, Field

from app.dependencies import get_llm
from orchestrator.state import HRState
from utils.logger import get_logger

logger = get_logger(__name__)


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
# Prompt
# ---------------------------------------------------------------------------

INTENT_PROMPT = """\
You are an HR intent classifier. Analyze the employee's message and determine
their intent.

RECENT CONVERSATION HISTORY:
{conversation_history}

TICKET CONTEXT:
{ticket_context}

CURRENT EMPLOYEE MESSAGE:
{message}

Classify into exactly ONE of these categories:
- employee_complaint: The employee is raising a NEW complaint, reporting an issue, \
expressing dissatisfaction about a person, policy, or working condition. \
ALSO use this if the recent history shows an ongoing complaint conversation \
and the employee is replying with follow-up details, confirmations like \
"yes", "no", "that's all", "go ahead", etc. \
ALSO use this if the employee is expressing dissatisfaction with a resolved/closed \
ticket or saying things are NOT resolved.
- leave_request: The employee wants to apply for leave, check leave balance, \
or ask about time off.
- payroll_query: The employee is asking about salary, payslips, deductions, \
bonuses, or compensation.
- policy_question: The employee is asking about company policies, rules, \
guidelines, or procedures.
- general_query: Greetings, small talk, positive feedback about resolved tickets, \
or anything that does not fit the above categories.

IMPORTANT RULES:
1. If the conversation history shows the employee was recently discussing a \
complaint and their current message is a short reply or confirmation, \
classify it as employee_complaint (not general_query).
2. If the employee has open/in-progress tickets and is asking about the status, \
classify as general_query (the AI will handle ticket status awareness).
3. If the employee has a resolved ticket and is saying they are NOT satisfied \
or the issue is NOT resolved, classify as employee_complaint.
4. If the employee has a resolved ticket and is saying they ARE satisfied or \
giving positive feedback, classify as general_query.
5. CRITICAL: If the last HR Assistant message in the conversation history shows \
a ticket was ALREADY CREATED (contains phrases like "Complaint Has Been Registered", \
"Ticket ID:", "TKT-", or a ticket confirmation), the complaint is ALREADY HANDLED. \
Classify as general_query UNLESS the employee is clearly raising a completely NEW \
and DIFFERENT complaint topic. Greetings, short replies, or references to the \
same complaint must be general_query.

Return the intent and your confidence (0.0 – 1.0).
"""


# ---------------------------------------------------------------------------
# Router function (graph node)
# ---------------------------------------------------------------------------

def classify_intent(state: HRState) -> dict:
    """Classify the user's intent using an LLM.

    Returns dict with ``intent`` and ``confidence``.
    """
    trace_id = state.get("trace_id", "N/A")
    message = state.get("message", "")

    logger.info(f"[{trace_id}] Classifying intent for message: {message[:80]}...")

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(IntentClassification)

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
