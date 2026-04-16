"""Memory store implementations — In-memory fallback + PostgreSQL."""

from typing import Protocol, runtime_checkable
from datetime import datetime, timezone

from utils.logger import get_logger
from memory.schemas import ConversationEntry, ComplaintRecord

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

@runtime_checkable
class BaseMemoryStore(Protocol):
    """Protocol that any memory backend must implement."""

    def save_conversation(self, entry: ConversationEntry) -> None: ...
    def get_conversation(self, user_id: str) -> list[ConversationEntry]: ...
    def save_complaint(self, record: ComplaintRecord) -> None: ...
    def get_complaints_by_user(self, user_id: str) -> list[ComplaintRecord]: ...


# ---------------------------------------------------------------------------
# In-memory implementation (fallback)
# ---------------------------------------------------------------------------

class InMemoryStore:
    """Dict-backed store — used as fallback when no DB is configured."""

    def __init__(self) -> None:
        self._conversations: dict[str, list[ConversationEntry]] = {}
        self._complaints: dict[str, list[ComplaintRecord]] = {}

    def save_conversation(self, entry: ConversationEntry) -> None:
        self._conversations.setdefault(entry.user_id, []).append(entry)
        logger.info(
            f"[{entry.trace_id}] Saved conversation (in-memory) for user {entry.user_id}"
        )

    def get_conversation(self, user_id: str) -> list[ConversationEntry]:
        return self._conversations.get(user_id, [])

    def save_complaint(self, record: ComplaintRecord) -> None:
        self._complaints.setdefault(record.user_id, []).append(record)
        logger.info(
            f"[{record.trace_id}] Saved complaint (in-memory) {record.complaint_id}"
        )

    def get_complaints_by_user(self, user_id: str) -> list[ComplaintRecord]:
        return self._complaints.get(user_id, [])


# ---------------------------------------------------------------------------
# PostgreSQL implementation (persistent — long-term storage)
# ---------------------------------------------------------------------------

class PostgresMemoryStore:
    """PostgreSQL-backed store — persists data across restarts.

    Data survives indefinitely (or until you purge it). Indexed for
    fast retrieval by user_id and timestamp.
    """

    def __init__(self) -> None:
        from db.connection import get_session_factory, get_engine
        from db.models import Base

        self._session_factory = get_session_factory()

        # Auto-create tables on first use
        engine = get_engine()
        Base.metadata.create_all(engine)
        logger.info("PostgreSQL memory store initialized — tables verified")

    def save_conversation(self, entry: ConversationEntry) -> None:
        """Insert a conversation row into PostgreSQL."""
        from db.models import ConversationModel

        try:
            with self._session_factory() as session:
                row = ConversationModel(
                    entry_id=entry.entry_id,
                    user_id=entry.user_id,
                    message=entry.message,
                    response=entry.response,
                    intent=entry.intent,
                    emotion=entry.emotion,
                    severity=entry.severity,
                    agent_used=entry.agent_used,
                    trace_id=entry.trace_id,
                    timestamp=datetime.fromisoformat(entry.timestamp)
                    if entry.timestamp
                    else datetime.now(timezone.utc),
                )
                session.add(row)
                session.commit()
            logger.info(
                f"[{entry.trace_id}] Saved conversation (PG) for user "
                f"{entry.user_id} (intent={entry.intent}, agent={entry.agent_used})"
            )
        except Exception as e:
            logger.error(f"[{entry.trace_id}] Failed to save conversation to PG: {e}")

    def get_conversation(self, user_id: str) -> list[ConversationEntry]:
        """Fetch all conversations for a user, ordered by timestamp."""
        from db.models import ConversationModel

        try:
            with self._session_factory() as session:
                rows = (
                    session.query(ConversationModel)
                    .filter(ConversationModel.user_id == user_id)
                    .order_by(ConversationModel.timestamp.asc())
                    .all()
                )
                return [
                    ConversationEntry(
                        entry_id=r.entry_id,
                        user_id=r.user_id,
                        message=r.message,
                        response=r.response or "",
                        intent=r.intent or "",
                        emotion=r.emotion or "",
                        severity=r.severity or "",
                        agent_used=r.agent_used or "",
                        trace_id=r.trace_id or "",
                        timestamp=r.timestamp.isoformat() if r.timestamp else "",
                    )
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Failed to fetch conversations from PG for {user_id}: {e}")
            return []

    def save_complaint(self, record: ComplaintRecord) -> None:
        """Insert a complaint row into PostgreSQL."""
        from db.models import ComplaintModel

        try:
            with self._session_factory() as session:
                row = ComplaintModel(
                    complaint_id=record.complaint_id,
                    user_id=record.user_id,
                    message=record.message,
                    complaint_type=record.complaint_type,
                    emotion=record.emotion,
                    severity=record.severity,
                    escalation_action=record.escalation_action,
                    ticket_id=record.ticket_id,
                    trace_id=record.trace_id,
                    timestamp=datetime.fromisoformat(record.timestamp)
                    if record.timestamp
                    else datetime.now(timezone.utc),
                )
                session.add(row)
                session.commit()
            logger.info(
                f"[{record.trace_id}] Saved complaint (PG) {record.complaint_id} "
                f"for user {record.user_id} (severity={record.severity})"
            )
        except Exception as e:
            logger.error(f"[{record.trace_id}] Failed to save complaint to PG: {e}")

    def get_complaints_by_user(self, user_id: str) -> list[ComplaintRecord]:
        """Fetch all complaints for a user, ordered by timestamp."""
        from db.models import ComplaintModel

        try:
            with self._session_factory() as session:
                rows = (
                    session.query(ComplaintModel)
                    .filter(ComplaintModel.user_id == user_id)
                    .order_by(ComplaintModel.timestamp.asc())
                    .all()
                )
                return [
                    ComplaintRecord(
                        complaint_id=r.complaint_id,
                        user_id=r.user_id,
                        message=r.message,
                        complaint_type=r.complaint_type or "",
                        emotion=r.emotion or "",
                        severity=r.severity or "",
                        escalation_action=r.escalation_action or "",
                        ticket_id=r.ticket_id or "",
                        trace_id=r.trace_id or "",
                        timestamp=r.timestamp.isoformat() if r.timestamp else "",
                    )
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Failed to fetch complaints from PG for {user_id}: {e}")
            return []
