"""Complaint classifier — detects type, emotion, severity via LLM."""

from app.dependencies import get_llm
from agents.complaint.prompts import CLASSIFIER_PROMPT
from agents.complaint.schemas import ComplaintClassification
from orchestrator.state import HRState
from utils.logger import get_logger

logger = get_logger(__name__)


def classify_complaint(state: HRState) -> dict:
    """Classify an employee complaint using LLM structured output.

    Updates state with: complaint_type, emotion, severity.
    """
    trace_id = state.get("trace_id", "N/A")
    user_id = state.get("user_id", "unknown")
    message = state.get("message", "")

    logger.info(f"[{trace_id}] Classifying complaint for user {user_id}")

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(ComplaintClassification)

        prompt = CLASSIFIER_PROMPT.format(message=message)
        result: ComplaintClassification = structured_llm.invoke(prompt)

        logger.info(
            f"[{trace_id}] Classification: type={result.complaint_type}, "
            f"emotion={result.emotion}, severity={result.severity}"
        )

        return {
            "complaint_type": result.complaint_type,
            "emotion": result.emotion,
            "severity": result.severity,
        }

    except Exception as e:
        logger.error(f"[{trace_id}] Error in classify_complaint: {e}")
        return {
            "complaint_type": "other",
            "emotion": "neutral",
            "severity": "medium",
        }
