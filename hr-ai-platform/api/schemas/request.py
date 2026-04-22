"""Request schemas for the API layer."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat message from an employee."""

    user_id: str = Field(
        default="anonymous",
        description="Unique employee identifier (used as fallback when not authenticated)",
        examples=["EMP001"],
    )
    message: str = Field(
        ..., description="The employee's message", examples=["I want to apply for leave"]
    )
    privacy_mode: str = Field(
        default="identified",
        description="Complaint privacy preference: identified, confidential, or anonymous",
        pattern="^(identified|confidential|anonymous)$",
    )
