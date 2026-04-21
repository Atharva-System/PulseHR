"""Escalation: notify HR personnel of urgent matters via SMTP email."""

from datetime import datetime, timezone
from typing import List

from app.config import settings
from db.connection import get_db_session
from db.models import UserModel
from skills.communication.email import send_email
from utils.logger import get_logger

logger = get_logger(__name__)


def _get_notification_recipients(role: str = "hr") -> List[str]:
    """Return email addresses of active users with receive_notifications enabled.

    Falls back to the SMTP_TO_HR / SMTP_TO_AUTHORITY env setting if no
    users are found in the database.
    """
    session = get_db_session()
    try:
        users = (
            session.query(UserModel)
            .filter(
                UserModel.role == role,
                UserModel.is_active == True,
                UserModel.receive_notifications == True,
            )
            .all()
        )
        emails = [u.email for u in users if u.email]
        if emails:
            return emails
    finally:
        session.close()

    # Fallback to env setting
    fallback = settings.smtp_to_hr if role == "hr" else settings.smtp_to_authority
    return [fallback] if fallback else []


def _build_html_email(complaint_summary: str, severity: str) -> str:
    """Build a professional HTML email body."""
    severity_upper = severity.upper()
    severity_colors = {
        "low": ("#22c55e", "#f0fdf4"),
        "medium": ("#eab308", "#fefce8"),
        "high": ("#f97316", "#fff7ed"),
        "critical": ("#ef4444", "#fef2f2"),
    }
    color, bg = severity_colors.get(severity, ("#f97316", "#fff7ed"))
    now = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")

    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Roboto,Arial,sans-serif;background:#f1f5f9;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:28px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <span style="font-size:24px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">⚠️ HR Alert</span>
                  <br/>
                  <span style="font-size:13px;color:rgba(255,255,255,0.8);margin-top:4px;display:inline-block;">PulseHR AI — Automated Notification</span>
                </td>
                <td align="right">
                  <span style="background:{bg};color:{color};font-size:13px;font-weight:700;padding:6px 16px;border-radius:20px;">{severity_upper}</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:32px;">
            <p style="margin:0 0 8px;font-size:13px;color:#64748b;text-transform:uppercase;letter-spacing:1px;font-weight:600;">Complaint Summary</p>
            <div style="background:#f8fafc;border-left:4px solid {color};border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:24px;">
              <p style="margin:0;font-size:15px;color:#1e293b;line-height:1.6;">{complaint_summary}</p>
            </div>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
              <tr>
                <td width="50%" style="padding:12px 16px;background:#f8fafc;border-radius:8px;">
                  <p style="margin:0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Severity Level</p>
                  <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:{color};">{severity_upper}</p>
                </td>
                <td width="16"></td>
                <td width="50%" style="padding:12px 16px;background:#f8fafc;border-radius:8px;">
                  <p style="margin:0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Reported At</p>
                  <p style="margin:4px 0 0;font-size:14px;font-weight:600;color:#1e293b;">{now}</p>
                </td>
              </tr>
            </table>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="center" style="padding:8px 0;">
                  <a href="#" style="display:inline-block;background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#ffffff;font-size:14px;font-weight:600;padding:12px 32px;border-radius:8px;text-decoration:none;">Review in Dashboard →</a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:20px 32px;">
            <p style="margin:0;font-size:12px;color:#94a3b8;text-align:center;">This is an automated alert from <strong style="color:#64748b;">PulseHR AI</strong>. Please do not reply to this email.</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def notify_hr(complaint_summary: str, severity: str) -> dict:
    """Alert HR team about a complaint that requires immediate attention.

    Sends a professional HTML email via SMTP to all HR users with
    receive_notifications enabled. Falls back to SMTP_TO_HR env value.
    """
    subject = f"⚠️ HR Alert — {severity.upper()} Severity Complaint Reported"
    body = _build_html_email(complaint_summary, severity)

    recipients = _get_notification_recipients(role="hr")
    if not recipients:
        logger.warning("No HR notification recipients found — skipping email")
        return {"status": "skipped", "reason": "no recipients"}

    logger.info(f"Notifying HR ({', '.join(recipients)}) — severity={severity}")

    results = []
    for recipient in recipients:
        results.append(send_email(to=recipient, subject=subject, body=body, html=True))
    return {"status": "sent", "recipients": recipients, "results": results}


def notify_authority(complaint_summary: str, severity: str) -> dict:
    """Alert Higher Authority about a critical/high SLA breach.

    Sends the same professional HTML email to all higher_authority users
    with receive_notifications enabled. Falls back to SMTP_TO_AUTHORITY env.
    """
    subject = f"🚨 ESCALATION — {severity.upper()} SLA Breach Requires Immediate Attention"
    body = _build_html_email(complaint_summary, severity)

    recipients = _get_notification_recipients(role="higher_authority")
    if not recipients:
        # Final fallback to env setting
        fallback = settings.smtp_to_authority
        recipients = [fallback] if fallback else []
    if not recipients:
        logger.warning("No Authority notification recipients found — skipping email")
        return {"status": "skipped", "reason": "no recipients"}

    logger.info(f"Notifying Authority ({', '.join(recipients)}) — severity={severity}")

    results = []
    for recipient in recipients:
        results.append(send_email(to=recipient, subject=subject, body=body, html=True))
    return {"status": "sent", "recipients": recipients, "results": results}
