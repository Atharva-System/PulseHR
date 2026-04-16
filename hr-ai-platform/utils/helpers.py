"""Shared utility functions."""

import uuid
from datetime import datetime, timezone


def generate_trace_id() -> str:
    """Generate a unique trace ID for request tracking."""
    return str(uuid.uuid4())


def get_timestamp() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with an optional prefix.

    Args:
        prefix: String prefix for the ID (e.g. 'TKT', 'CMP').

    Returns:
        Unique identifier string like 'TKT-a1b2c3d4'.
    """
    short_id = uuid.uuid4().hex[:8]
    if prefix:
        return f"{prefix}-{short_id}"
    return short_id
