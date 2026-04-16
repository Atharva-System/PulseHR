"""Pydantic schemas for the Complaint Agent."""

from typing import List
from pydantic import BaseModel, Field


class ComplaintClassification(BaseModel):
    """Structured output from the complaint classifier LLM call."""

    complaint_type: str = Field(
        description="One of: manager_issue, harassment, workload, discrimination, workplace_safety, other"
    )
    emotion: str = Field(
        description="Detected emotion: frustration, anger, stress, sadness, neutral"
    )
    severity: str = Field(
        description="Severity level: low, medium, high, critical"
    )
    reasoning: str = Field(
        default="",
        description="Brief reasoning for the classification",
    )


class SafetyCheckResult(BaseModel):
    """Output of the safety-check step."""

    is_immediate_danger: bool = Field(
        description="True if the complaint describes immediate physical danger or legal emergency"
    )
    explanation: str = Field(
        default="",
        description="Why this was flagged or not",
    )


class InfoCompletenessResult(BaseModel):
    """Output of the info-completeness check."""

    status: str = Field(
        description="GATHERING if more info needed, COMPLETE if ready to file"
    )
    missing_info: List[str] = Field(
        default_factory=list,
        description="List of missing information items",
    )
    reasoning: str = Field(
        default="",
        description="Brief reasoning for the decision",
    )


class ComplaintResponse(BaseModel):
    """Final response payload from the complaint agent."""

    message: str
    escalation_action: str = ""
    ticket_id: str = ""


class PolicyViolationResult(BaseModel):
    """Output of the policy-violation check."""

    is_policy_violation: bool = Field(
        description="True if the complaint clearly describes a violation of a company policy"
    )
    matched_policy: str = Field(
        default="",
        description="Name of the matched policy (e.g., 'posh_policy', 'anti_harassment')"
    )
    policy_summary: str = Field(
        default="",
        description="Brief summary of which policy rule was violated"
    )
    reasoning: str = Field(
        default="",
        description="Brief reasoning for the decision"
    )
