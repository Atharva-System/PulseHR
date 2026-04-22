"""Privacy mode helpers for complaint reporting and ticket views.

Access matrix
─────────────
                 identified   confidential          anonymous
HR user_id       real         ❌ not visible        ❌ not visible
Admin user_id    real         real                  "Anonymous …"
HR chat list     ✅ visible   ❌ not in list        ❌ not in list
Admin chat list  ✅ visible   ✅ visible (badge)    ✅ placeholder
HR chat content  ✅ readable  ❌ not visible        ❌ not visible
Admin chat       ✅ readable  ✅ readable           ❌ not visible
HR ticket name   real         ❌ not in list        ❌ not in list
Admin ticket     real         real                  "Anonymous …"
"""

from __future__ import annotations

PRIVACY_IDENTIFIED = "identified"
PRIVACY_CONFIDENTIAL = "confidential"
PRIVACY_ANONYMOUS = "anonymous"

VALID_PRIVACY_MODES = {
    PRIVACY_IDENTIFIED,
    PRIVACY_CONFIDENTIAL,
    PRIVACY_ANONYMOUS,
}


def normalize_privacy_mode(value: str | None) -> str:
    """Normalize privacy mode to a supported value."""
    if not value:
        return PRIVACY_IDENTIFIED

    normalized = value.strip().lower()
    if normalized in VALID_PRIVACY_MODES:
        return normalized
    return PRIVACY_IDENTIFIED


def redact_reporter_label(user_id: str, privacy_mode: str, viewer_role: str) -> str:
    """Return the display label for user identity.

    - identified → always real user_id
    - confidential → real for higher_authority, redacted for hr
    - anonymous → always "Anonymous Employee"
    """
    mode = normalize_privacy_mode(privacy_mode)

    if mode == PRIVACY_IDENTIFIED:
        return user_id

    if mode == PRIVACY_CONFIDENTIAL:
        return user_id if viewer_role == "higher_authority" else "Confidential Employee"

    return "Anonymous Employee"


def can_view_chat_content(privacy_mode: str, viewer_role: str) -> bool:
    """Whether the viewer is allowed to read actual chat messages.

    - identified → everyone can read
    - confidential → only higher_authority
    - anonymous → nobody
    """
    mode = normalize_privacy_mode(privacy_mode)
    if mode == PRIVACY_IDENTIFIED:
        return True
    if mode == PRIVACY_CONFIDENTIAL:
        return viewer_role == "higher_authority"
    # anonymous
    return False


def can_view_user_in_list(privacy_mode: str, viewer_role: str) -> bool:
    """Whether a user row should appear in the conversation-user sidebar.

    - identified   → always visible
    - confidential → only higher_authority (HR sees nothing — no hint)
    - anonymous    → only higher_authority (placeholder row)
    """
    mode = normalize_privacy_mode(privacy_mode)
    if mode == PRIVACY_IDENTIFIED:
        return True
    # confidential and anonymous → only admin
    return viewer_role == "higher_authority"


# ---------------------------------------------------------------------------
# HR-target detection
# ---------------------------------------------------------------------------

_HR_KEYWORDS = {
    "hr", "human resources", "hr department", "hr team",
    "hr manager", "hr head", "hr representative", "hr rep",
}


def is_complaint_about_hr(complaint_target: str) -> bool:
    """Return True if the complaint target appears to be an HR staff member.

    Uses two strategies:
    1. Keyword matching  — target contains HR-related terms
    2. DB lookup         — target name matches a user with role 'hr'
    """
    if not complaint_target:
        return False

    target_lower = complaint_target.strip().lower()

    # --- Strategy 1: keyword check ---
    for kw in _HR_KEYWORDS:
        if kw in target_lower:
            return True

    # --- Strategy 2: DB lookup against HR users ---
    try:
        from db.connection import get_db_session
        from db.models import UserModel

        session = get_db_session()
        try:
            hr_users = (
                session.query(UserModel)
                .filter(UserModel.role == "hr")
                .all()
            )
            # Check if any HR user's name/username appears in the target
            for u in hr_users:
                uname = (u.username or "").strip().lower()
                fname = (u.full_name or "").strip().lower()
                if uname and uname in target_lower:
                    return True
                if fname and len(fname) > 2 and fname in target_lower:
                    return True
                # Also check if the target name appears in the HR user's name
                # e.g. target="Soham" matches full_name="Soham Bhalodi"
                target_parts = target_lower.split()
                for part in target_parts:
                    if len(part) > 2 and (part in fname or part in uname):
                        return True
        finally:
            session.close()
    except Exception:
        pass  # Fail open — prefer not blocking if DB is unavailable

    return False
