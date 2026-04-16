"""Skill: send notifications via configured channels."""

from skills.registry import registry
from utils.logger import get_logger

logger = get_logger(__name__)


@registry.tool
def send_notification(recipient: str, message: str, channel: str = "email") -> dict:
    """Send a notification to a recipient.

    Routes to the correct channel:
      - email: sends via SMTP
      - slack / sms: placeholder (logged only)

    Args:
        recipient: Target user or email address.
        message: Notification body.
        channel: Delivery channel — 'email', 'slack', or 'sms'.

    Returns:
        Confirmation dict.
    """
    if channel == "email":
        from skills.communication.email import send_email

        return send_email(
            to=recipient,
            subject="HR AI Platform — Notification",
            body=message,
        )

    # Slack / SMS — placeholder for now
    logger.info(f"Sending {channel} notification to {recipient}: {message[:80]}...")
    return {
        "status": "sent",
        "recipient": recipient,
        "channel": channel,
        "message_preview": message[:100],
    }
