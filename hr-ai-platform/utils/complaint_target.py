"""Helpers for resolving complaint target names to known user records."""

from __future__ import annotations

import re
from typing import Optional, TypedDict

from db.connection import get_db_session
from db.models import UserModel


class ComplaintTargetMatch(TypedDict):
    user_id: str
    full_name: str
    username: str
    role: str


_ROLE_PREFIXES = (
    "manager",
    "colleague",
    "supervisor",
    "team lead",
    "lead",
    "mr",
    "mrs",
    "ms",
    "miss",
    "hr",
    "employee",
)


def _normalize(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def _clean_target_query(text: str) -> str:
    value = _normalize(text)
    if not value:
        return ""

    for prefix in _ROLE_PREFIXES:
        if value.startswith(prefix + " "):
            value = value[len(prefix):].strip()
            break

    for splitter in (" from ", " in ", " of ", " at "):
        if splitter in value:
            value = value.split(splitter, 1)[0].strip()
            break

    return value


def resolve_complaint_target(text: str) -> Optional[ComplaintTargetMatch]:
    """Resolve a spoken/written complaint target to a known user.

    Uses permissive name matching so partial mentions like "Dixit"
    can map to "Dixit Gajjar" when the match is strong and unique.
    """
    query = _clean_target_query(text)
    if not query:
        return None

    query_tokens = query.split()
    if not query_tokens:
        return None

    session = get_db_session()
    try:
        users = session.query(UserModel).filter(UserModel.is_active == True).all()  # noqa: E712
        scored: list[tuple[int, UserModel]] = []

        for user in users:
            full_name = (user.full_name or "").strip()
            username = (user.username or "").strip()
            full_norm = _normalize(full_name)
            user_norm = _normalize(username)
            full_tokens = full_norm.split()
            user_tokens = user_norm.split()

            score = 0
            if query == full_norm or query == user_norm:
                score = 120
            elif full_norm.startswith(query) or user_norm.startswith(query):
                score = 100
            elif all(token in full_tokens for token in query_tokens):
                score = 90
            elif all(token in user_tokens for token in query_tokens):
                score = 85
            elif len(query_tokens) == 1:
                token = query_tokens[0]
                if token in full_tokens:
                    score = 80
                elif token in user_tokens:
                    score = 75
                elif full_norm.startswith(token + " "):
                    score = 70
                elif user_norm.startswith(token):
                    score = 65

            if score > 0:
                scored.append((score, user))

        if not scored:
            return None

        scored.sort(key=lambda item: item[0], reverse=True)
        top_score = scored[0][0]
        top_matches = [u for score, u in scored if score == top_score]
        if len(top_matches) != 1:
            return None

        user = top_matches[0]
        return ComplaintTargetMatch(
            user_id=user.id,
            full_name=(user.full_name or user.username or "").strip(),
            username=(user.username or "").strip(),
            role=(user.role or "").strip(),
        )
    finally:
        session.close()
