"""Global shared state schema for the LangGraph workflow."""

from typing import TypedDict


class HRState(TypedDict, total=False):
    """Shared state passed through every node in the orchestrator graph.

    All fields are optional (total=False) so that nodes only return the
    keys they update.
    """

    # --- Core request data ---
    user_id: str
    message: str
    privacy_mode: str
    thread_id: str

    # --- Router output ---
    intent: str
    confidence: float

    # --- Sentiment / classification ---
    emotion: str
    severity: str
    complaint_type: str
    complaint_target: str

    # --- Agent output ---
    response: str
    escalation_action: str

    # --- Conversation context ---
    conversation_history: list[dict]

    # --- Ticket awareness ---
    ticket_context: dict

    # --- Metadata & tracing ---
    trace_id: str
    timestamp: str
    agent_used: str
    metadata: dict
