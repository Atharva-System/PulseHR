"""Response schemas for the API layer."""

from typing import Any

from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """Response returned to the client after processing a chat message."""

    user_id: str
    response: str
    intent: str = ""
    confidence: float = 0.0
    agent_used: str = ""
    trace_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
