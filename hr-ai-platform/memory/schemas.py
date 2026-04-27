"""Pydantic models for memory records."""

from pydantic import BaseModel, Field

from utils.helpers import generate_id, get_timestamp


class ConversationEntry(BaseModel):
    """A single conversation turn stored in memory.

    Stores **full context** — not just message/response, but also
    intent, emotion, severity, and which agent handled the request.
    """

    entry_id: str = Field(default_factory=lambda: generate_id("CONV"))
    user_id: str
    message: str
    response: str = ""
    intent: str = ""
    emotion: str = ""
    severity: str = ""
    agent_used: str = ""
    privacy_mode: str = "identified"
    thread_id: str = ""
    trace_id: str = ""
    timestamp: str = Field(default_factory=get_timestamp)


class ComplaintRecord(BaseModel):
    """A complaint record stored in memory."""

    complaint_id: str = Field(default_factory=lambda: generate_id("CMP"))
    user_id: str
    message: str
    complaint_type: str = ""
    emotion: str = ""
    severity: str = ""
    privacy_mode: str = "identified"
    thread_id: str = ""
    complaint_target: str = ""
    complaint_target_user_id: str = ""
    escalation_action: str = ""
    ticket_id: str = ""
    trace_id: str = ""
    timestamp: str = Field(default_factory=get_timestamp)
