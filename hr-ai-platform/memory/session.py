"""Conversation session management."""

from utils.helpers import generate_id, get_timestamp
from utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Lightweight session tracker for active conversations."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}

    def create_session(self, user_id: str) -> str:
        """Start a new session for a user, returning the session ID."""
        session_id = generate_id("SES")
        self._sessions[session_id] = {
            "user_id": user_id,
            "started_at": get_timestamp(),
            "ended_at": None,
            "turns": 0,
        }
        logger.info(f"Session {session_id} created for user {user_id}")
        return session_id

    def get_session(self, session_id: str) -> dict | None:
        """Retrieve session data by ID."""
        return self._sessions.get(session_id)

    def increment_turn(self, session_id: str) -> None:
        """Record that another exchange happened in this session."""
        if session_id in self._sessions:
            self._sessions[session_id]["turns"] += 1

    def end_session(self, session_id: str) -> None:
        """Mark a session as ended."""
        if session_id in self._sessions:
            self._sessions[session_id]["ended_at"] = get_timestamp()
            logger.info(f"Session {session_id} ended")
