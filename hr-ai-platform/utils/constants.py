"""Enums and constants used across the HR AI Platform."""

from enum import StrEnum


class Intent(StrEnum):
    """Supported user intent types."""

    EMPLOYEE_COMPLAINT = "employee_complaint"
    LEAVE_REQUEST = "leave_request"
    PAYROLL_QUERY = "payroll_query"
    POLICY_QUESTION = "policy_question"
    GENERAL_QUERY = "general_query"


class Emotion(StrEnum):
    """Detectable user emotions."""

    FRUSTRATION = "frustration"
    ANGER = "anger"
    STRESS = "stress"
    SADNESS = "sadness"
    NEUTRAL = "neutral"


class Severity(StrEnum):
    """Complaint / issue severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplaintType(StrEnum):
    """Types of employee complaints."""

    MANAGER_ISSUE = "manager_issue"
    HARASSMENT = "harassment"
    WORKLOAD = "workload"
    DISCRIMINATION = "discrimination"
    WORKPLACE_SAFETY = "workplace_safety"
    OTHER = "other"


class EscalationAction(StrEnum):
    """Actions the escalation layer can take."""

    NOTIFY_HR = "notify_hr"
    CREATE_TICKET = "create_ticket"
    LOG_ONLY = "log_only"
