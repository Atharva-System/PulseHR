"""Skill: send email via SMTP."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings
from skills.registry import registry
from utils.logger import get_logger

logger = get_logger(__name__)


@registry.tool
def send_email(to: str, subject: str, body: str, html: bool = False) -> dict:
    """Send an email via SMTP.

    Uses the SMTP credentials from app config (.env).
    Falls back to logging if SMTP is not configured.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body content (plain text or HTML).
        html: If True, sends body as HTML.

    Returns:
        Confirmation dict with status.
    """
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning(f"SMTP not configured — email to {to} logged only")
        return {
            "status": "skipped",
            "reason": "SMTP credentials not configured",
            "to": to,
            "subject": subject,
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject

        if html:
            msg.attach(MIMEText(body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        logger.info(f"Email sent to {to} — subject: {subject}")
        return {
            "status": "sent",
            "to": to,
            "subject": subject,
        }

    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return {
            "status": "failed",
            "to": to,
            "subject": subject,
            "error": str(e),
        }
