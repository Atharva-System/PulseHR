"""Escalation: audit trail — persisted to PostgreSQL."""

import json

from utils.helpers import generate_id, get_timestamp
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_session_factory():
    from db.connection import get_session_factory
    return get_session_factory()


def log_event(event_type: str, details: dict, trace_id: str = "") -> None:
    """Persist an audit event to PostgreSQL.

    Args:
        event_type: e.g. 'complaint_escalated', 'ticket_created'.
        details: Arbitrary event payload (stored as JSON text).
        trace_id: Request trace ID for correlation.
    """
    from db.models import AuditLogModel

    try:
        session_factory = _get_session_factory()
        with session_factory() as session:
            row = AuditLogModel(
                id=generate_id("AUD"),
                event_type=event_type,
                details=json.dumps(details),
                trace_id=trace_id,
            )
            session.add(row)
            session.commit()
        logger.info(f"[{trace_id}] Audit (PG): {event_type} — {details}")
    except Exception as e:
        logger.error(f"[{trace_id}] Failed to save audit event to PG: {e}")


def get_audit_log(trace_id: str = "") -> list[dict]:
    """Retrieve audit events, optionally filtered by trace_id."""
    from db.models import AuditLogModel

    try:
        session_factory = _get_session_factory()
        with session_factory() as session:
            query = session.query(AuditLogModel).order_by(AuditLogModel.timestamp.desc())
            if trace_id:
                query = query.filter_by(trace_id=trace_id)
            rows = query.limit(100).all()
            return [
                {
                    "id": r.id,
                    "event_type": r.event_type,
                    "details": json.loads(r.details) if r.details else {},
                    "trace_id": r.trace_id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else "",
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"Failed to fetch audit log: {e}")
    return []
