"""SQLAlchemy ORM models for the HR AI Platform."""

from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Text, DateTime, Boolean, Index
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_engine():
    """Convenience re-export of the engine getter."""
    from db.connection import get_engine as _get_engine
    return _get_engine()


# ---------------------------------------------------------------------------
# Users / Auth
# ---------------------------------------------------------------------------

class UserModel(Base):
    """Application users with role-based access."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True)  # UUID
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    full_name = Column(String(120), default="")
    role = Column(String(20), nullable=False, default="user")  # user | hr | higher_authority
    is_active = Column(Boolean, default=True, index=True)
    receive_notifications = Column(Boolean, default=False, index=True)  # ticket email notifications
    notification_levels = Column(String(200), default="critical,high,medium,low")  # comma-separated severity levels
    created_by = Column(String(36), nullable=True)  # user id who created this account
    last_login = Column(DateTime(timezone=True), nullable=True)  # current login timestamp
    previous_login = Column(DateTime(timezone=True), nullable=True)  # previous login timestamp
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_users_role_active", "role", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User {self.username} role={self.role}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "receive_notifications": self.receive_notifications or False,
            "notification_levels": [l for l in (self.notification_levels or "").split(",") if l],
            "created_by": self.created_by,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "previous_login": self.previous_login.isoformat() if self.previous_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationModel(Base):
    """Stores every conversation turn with full context."""

    __tablename__ = "conversations"

    entry_id = Column(String(20), primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text, default="")
    intent = Column(String(50), default="")
    emotion = Column(String(50), default="")
    severity = Column(String(20), default="")
    agent_used = Column(String(50), default="")
    privacy_mode = Column(String(20), default="identified", index=True)
    thread_id = Column(String(20), default="", index=True)
    trace_id = Column(String(50), default="", index=True)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_conv_user_time", "user_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.entry_id} user={self.user_id}>"


class ComplaintModel(Base):
    """Stores complaint records with escalation details."""

    __tablename__ = "complaints"

    complaint_id = Column(String(20), primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    complaint_type = Column(String(50), default="")
    emotion = Column(String(50), default="")
    severity = Column(String(20), default="", index=True)
    privacy_mode = Column(String(20), default="identified", index=True)
    thread_id = Column(String(20), default="", index=True)
    complaint_target = Column(String(200), default="")
    escalation_action = Column(String(30), default="")
    ticket_id = Column(String(20), default="")
    trace_id = Column(String(50), default="", index=True)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_comp_user_time", "user_id", "timestamp"),
        Index("ix_comp_severity_time", "severity", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Complaint {self.complaint_id} user={self.user_id} severity={self.severity}>"


class TicketModel(Base):
    """Stores HR support tickets."""

    __tablename__ = "tickets"

    ticket_id = Column(String(20), primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    severity = Column(String(20), default="", index=True)
    privacy_mode = Column(String(20), default="identified", index=True)
    thread_id = Column(String(20), default="", index=True)
    complaint_target = Column(String(200), default="")
    assignee = Column(String(100), default="hr-team")
    assignee_id = Column(String(36), nullable=True)       # FK-style to users.id
    status = Column(String(20), default="open", index=True)
    user_id = Column(String(50), default="", index=True)
    trace_id = Column(String(50), default="", index=True)
    sla_deadline = Column(DateTime(timezone=True), nullable=True)
    sla_breached = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_ticket_severity_status", "severity", "status"),
    )

    def __repr__(self) -> str:
        return f"<Ticket {self.ticket_id} severity={self.severity} status={self.status}>"


class TicketCommentModel(Base):
    """Internal notes / comments on tickets by HR staff."""

    __tablename__ = "ticket_comments"

    id = Column(String(20), primary_key=True)
    ticket_id = Column(String(20), nullable=False, index=True)
    user_id = Column(String(36), nullable=False)      # who wrote the comment
    username = Column(String(50), default="")
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=True)        # internal note vs public reply
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<TicketComment {self.id} ticket={self.ticket_id}>"


class FeedbackModel(Base):
    """User feedback / rating after complaint resolution."""

    __tablename__ = "feedback"

    id = Column(String(20), primary_key=True)
    ticket_id = Column(String(20), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    rating = Column(Float, nullable=False)             # 1-5
    comment = Column(Text, default="")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Feedback {self.id} ticket={self.ticket_id} rating={self.rating}>"


class MessageModel(Base):
    """Internal messages between HR staff and Higher Authority."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)       # UUID
    sender_id = Column(String(36), nullable=False, index=True)    # users.id
    sender_username = Column(String(50), default="")
    sender_role = Column(String(20), default="")
    recipient_id = Column(String(36), nullable=False, index=True) # users.id
    recipient_username = Column(String(50), default="")
    recipient_role = Column(String(20), default="")
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_messages_sender_recipient", "sender_id", "recipient_id"),
    )

    def __repr__(self) -> str:
        return f"<Message {self.id} from={self.sender_username} to={self.recipient_username}>"


class PolicyModel(Base):
    """Stores HR policies — editable by HR / authority from the dashboard."""

    __tablename__ = "policies"

    id = Column(String(36), primary_key=True)  # UUID
    policy_key = Column(String(80), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    keywords = Column(Text, default="")           # comma-separated keywords
    is_active = Column(Boolean, default=True, index=True)
    updated_by = Column(String(50), default="")    # username who last edited
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Policy {self.policy_key}>"


class AuditLogModel(Base):
    """Stores audit trail for all escalation events."""

    __tablename__ = "audit_log"

    id = Column(String(20), primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)
    details = Column(Text, default="")
    trace_id = Column(String(50), default="", index=True)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} type={self.event_type}>"


class AgentConfigModel(Base):
    """Stores per-agent LLM configuration — persisted across restarts."""

    __tablename__ = "agent_configs"

    id = Column(String(50), primary_key=True)  # e.g. "complaint_agent"
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    intent = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    model_name = Column(String(200), nullable=False)
    temperature = Column(Float, default=1.0)
    top_p = Column(Float, default=1.0)
    max_tokens = Column(Float, default=4096)
    updated_by = Column(String(50), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<AgentConfig {self.id} model={self.model_name}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "intent": self.intent,
            "is_active": self.is_active,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": int(self.max_tokens),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
        }


class AppNotificationModel(Base):
    """In-app notifications for HR / authority users."""

    __tablename__ = "app_notifications"

    id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(String(36), nullable=False, index=True)  # recipient users.id
    type = Column(String(30), nullable=False, default="new_ticket")  # new_ticket | high_severity | status_change | escalation
    title = Column(String(300), nullable=False)
    message = Column(Text, default="")
    severity = Column(String(20), default="")
    ticket_id = Column(String(20), default="", index=True)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    __table_args__ = (
        Index("ix_appnotif_user_read", "user_id", "is_read"),
    )

    def __repr__(self) -> str:
        return f"<AppNotification {self.id} user={self.user_id} type={self.type}>"
