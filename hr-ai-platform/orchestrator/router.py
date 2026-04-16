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

CURRENT EMPLOYEE MESSAGE:
{message}

Classify into exactly ONE of these categories:
- employee_complaint: The employee is raising a complaint, reporting an issue, \
expressing dissatisfaction about a person, policy, or working condition. \
ALSO use this if the recent history shows an ongoing complaint conversation \
and the employee is replying with follow-up details, confirmations like \
"yes", "no", "that's all", "go ahead", etc.
- leave_request: The employee wants to apply for leave, check leave balance, \
or ask about time off.
- payroll_query: The employee is asking about salary, payslips, deductions, \
bonuses, or compensation.
- policy_question: The employee is asking about company policies, rules, \
guidelines, or procedures.
- general_query: Greetings, small talk, or anything that does not fit the \
above categories.

IMPORTANT: If the conversation history shows the employee was recently \
discussing a complaint and their current message is a short reply or \
confirmation, classify it as employee_complaint (not general_query).

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

        prompt = INTENT_PROMPT.format(
            message=message,
            conversation_history=history_str,
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
