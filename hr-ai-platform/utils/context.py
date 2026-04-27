"""Helpers for building compact, prompt-safe conversation context."""

from __future__ import annotations

TICKET_MARKERS = (
    "Complaint Has Been Registered",
    "Ticket ID:",
    "TKT-",
    "ticket has been registered",
    "Re-opened & Escalated",
)


def contains_ticket_notice(text: str) -> bool:
    """Return True if the text contains a ticket-registration UI block."""
    if not text:
        return False
    return any(marker in text for marker in TICKET_MARKERS)


def strip_ticket_notice(text: str) -> str:
    """Remove large ticket/status UI blocks from assistant text before prompting."""
    if not text:
        return ""

    if "\n\n---\n\n" in text:
        text = text.split("\n\n---\n\n", 1)[0]

    lines = []
    for line in text.splitlines():
        if any(marker in line for marker in TICKET_MARKERS):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _truncate(text: str, max_chars: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def build_compact_history(
    entries: list[dict],
    *,
    max_turns: int = 3,
    max_chars_per_message: int = 280,
    strip_ticket_blocks: bool = True,
) -> str:
    """Convert conversation entries into a compact history string."""
    if not entries:
        return "(none)"

    parts: list[str] = []
    for entry in entries[-max_turns:]:
        user_text = _truncate(entry.get("content", "") or "", max_chars_per_message)
        bot_text = entry.get("content2", "") or ""
        if strip_ticket_blocks:
            bot_text = strip_ticket_notice(bot_text)
        bot_text = _truncate(bot_text, max_chars_per_message)

        if user_text:
            parts.append(f"Employee: {user_text}")
        if bot_text:
            parts.append(f"HR Assistant: {bot_text}")

    return "\n".join(parts) if parts else "(none)"
