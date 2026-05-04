"""Escalation: notify HR / authority via email AND in-app notifications.

Recipients and their email addresses come from the DB (users table).
Each user's notification_levels control which severities they receive.
Both email and in-app notification are created per-recipient.
"""

import uuid
from datetime import datetime, timezone
from typing import List, NamedTuple

from app.config import settings
from db.connection import get_db_session
from db.models import UserModel, AppNotificationModel
from skills.communication.email import send_email
from utils.logger import get_logger

logger = get_logger(__name__)


class Recipient(NamedTuple):
    user_id: str
    email: str
    username: str


def _get_notification_recipients(role: str = "hr", severity: str = "") -> List[Recipient]:
    """Return Recipient(user_id, email, username) for active users matching role + severity.

    For HR: requires receive_notifications=True.
    For higher_authority: always includes all active users of that role.
    Filters by severity level stored in user's notification_levels.
    No fallback to env — DB is the source of truth.
    """
    session = get_db_session()
    try:
        q = session.query(UserModel).filter(
            UserModel.role == role,
            UserModel.is_active == True,
        )
        if role == "hr":
            q = q.filter(UserModel.receive_notifications == True)
        users = q.all()

        # Filter by severity level
        if severity:
            sev_lower = severity.strip().lower()
            filtered = []
            for u in users:
                levels = [l.strip().lower() for l in (getattr(u, "notification_levels", None) or "").split(",") if l.strip()]
                if sev_lower in levels:
                    filtered.append(u)
            users = filtered

        return [Recipient(user_id=u.id, email=u.email, username=u.username) for u in users if u.email]
    finally:
        session.close()


def _create_in_app_notification(
    user_id: str,
    notif_type: str,
    title: str,
    message: str,
    severity: str = "",
    ticket_id: str = "",
) -> None:
    """Insert an in-app notification row for a single user."""
    session = get_db_session()
    try:
        notif = AppNotificationModel(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=notif_type,
            title=title,
            message=message,
            severity=severity,
            ticket_id=ticket_id,
        )
        session.add(notif)
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning(f"Failed to create in-app notification for {user_id}: {e}")
    finally:
        session.close()


def _notify_recipients(
    recipients: List[Recipient],
    subject: str,
    body: str,
    notif_type: str,
    notif_title: str,
    notif_message: str,
    severity: str = "",
    ticket_id: str = "",
) -> dict:
    """Send email + create in-app notification for every recipient."""
    if not recipients:
        logger.warning("No notification recipients found — skipping")
        return {"status": "skipped", "reason": "no recipients"}

    emails_sent = []
    for r in recipients:
        # In-app notification
        _create_in_app_notification(
            user_id=r.user_id,
            notif_type=notif_type,
            title=notif_title,
            message=notif_message,
            severity=severity,
            ticket_id=ticket_id,
        )
        # Email
        result = send_email(to=r.email, subject=subject, body=body, html=True)
        emails_sent.append({"email": r.email, "result": result})

    logger.info(
        f"Notified {len(recipients)} recipients — "
        f"emails: {[r.email for r in recipients]}, severity={severity}"
    )
    return {"status": "sent", "recipients": [r.email for r in recipients], "results": emails_sent}


def _build_html_email(complaint_summary: str, severity: str, ticket_id: str = "", role: str = "hr") -> str:
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
    base_path = "admin" if role == "higher_authority" else "hr"
    frontend_base = settings.frontend_url.rstrip("/")
    dashboard_url = (
      f"{frontend_base}/#/{base_path}/tickets/{ticket_id}"
        if ticket_id
      else f"{frontend_base}/#/{base_path}/tickets"
    )

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
                  <span style="font-size:24px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">⚠️ Alert</span>
                  <br/>
                  <span style="font-size:13px;color:rgba(255,255,255,0.8);margin-top:4px;display:inline-block;">Pulsee AI — Automated Notification</span>
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
                  <a href="{dashboard_url}" style="display:inline-block;background:linear-gradient(135deg,#4f46e5,#7c3aed);color:#ffffff;font-size:14px;font-weight:600;padding:12px 32px;border-radius:8px;text-decoration:none;">Review in Dashboard →</a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:20px 32px;">
            <p style="margin:0;font-size:12px;color:#94a3b8;text-align:center;">This is an automated alert from <strong style="color:#64748b;">Pulsee AI</strong>. Please do not reply to this email.</p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def notify_hr(complaint_summary: str, severity: str) -> dict:
    """Alert HR team AND authority about a complaint — email + in-app notification.

    Recipients come from the DB. Both HR and higher_authority users whose
    notification_levels include the given severity will be notified.
    """
    subject = f"⚠️ Alert — {severity.upper()} Severity Complaint Reported"
    body_hr = _build_html_email(complaint_summary, severity, role="hr")
    body_auth = _build_html_email(complaint_summary, severity, role="higher_authority")

    hr_recipients = _get_notification_recipients(role="hr", severity=severity)
    authority_recipients = _get_notification_recipients(role="higher_authority", severity=severity)

    # Merge, deduplicate by user_id — send role-appropriate dashboard URL
    notif_type = "high_severity" if severity in ("critical", "high") else "new_ticket"
    notif_title = f"{'⚠️ Urgent: ' if severity in ('critical', 'high') else ''}New {severity.upper()} Complaint"
    notif_message = complaint_summary[:300]

    results = []
    if hr_recipients:
        results.append(_notify_recipients(
            recipients=hr_recipients,
            subject=subject,
            body=body_hr,
            notif_type=notif_type,
            notif_title=notif_title,
            notif_message=notif_message,
            severity=severity,
        ))
    if authority_recipients:
        results.append(_notify_recipients(
            recipients=authority_recipients,
            subject=subject,
            body=body_auth,
            notif_type=notif_type,
            notif_title=notif_title,
            notif_message=notif_message,
            severity=severity,
        ))
    return results[0] if len(results) == 1 else {"status": "sent", "results": results}


def notify_authority_hr_complaint(
    complaint_summary: str,
    severity: str,
    complaint_target: str,
    ticket_id: str = "",
    user_id: str = "",
) -> dict:
    """Alert Higher Authority when a complaint is directed at an HR staff member.

    This is a conflict-of-interest escalation — the regular HR team must NOT see
    this ticket. Only higher authority (admin) receives this alert.
    """
    severity_upper = severity.upper()
    severity_colors = {
        "low": ("#22c55e", "#f0fdf4"),
        "medium": ("#eab308", "#fefce8"),
        "high": ("#f97316", "#fff7ed"),
        "critical": ("#ef4444", "#fef2f2"),
    }
    color, bg = severity_colors.get(severity, ("#ef4444", "#fef2f2"))
    now = datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC")
    ticket_row = (
        f'<p style="margin:0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Ticket ID</p>'
        f'<p style="margin:4px 0 0;font-size:14px;font-weight:600;color:#1e293b;">{ticket_id}</p>'
        if ticket_id else ""
    )
    reporter_row = (
        f'<p style="margin:0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Reporter (confidential)</p>'
        f'<p style="margin:4px 0 0;font-size:14px;font-weight:600;color:#1e293b;">{user_id}</p>'
        if user_id else ""
    )

    body = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Roboto,Arial,sans-serif;background:#f1f5f9;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#dc2626,#9b1c1c);padding:28px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <span style="font-size:24px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">🚨 Conflict-of-Interest Escalation</span>
                  <br/>
                  <span style="font-size:13px;color:rgba(255,255,255,0.85);margin-top:6px;display:inline-block;">
                    Pulsee AI &mdash; Complaint Directed at HR Staff &mdash; Admin Eyes Only
                  </span>
                </td>
                <td align="right">
                  <span style="background:{bg};color:{color};font-size:13px;font-weight:700;padding:6px 16px;border-radius:20px;">{severity_upper}</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <!-- Alert Banner -->
        <tr>
          <td style="background:#fef2f2;border-left:4px solid #ef4444;padding:14px 24px;">
            <p style="margin:0;font-size:14px;color:#991b1b;font-weight:600;">
              &#9888;&nbsp; This complaint targets an HR team member (<strong>{complaint_target}</strong>).
              It has been automatically hidden from HR and escalated directly to you.
            </p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:32px;">
            <p style="margin:0 0 8px;font-size:13px;color:#64748b;text-transform:uppercase;letter-spacing:1px;font-weight:600;">Complaint Summary</p>
            <div style="background:#f8fafc;border-left:4px solid {color};border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:24px;">
              <p style="margin:0;font-size:15px;color:#1e293b;line-height:1.6;">{complaint_summary}</p>
            </div>
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;border-spacing:0 8px;">
              <tr>
                <td width="50%" style="padding:12px 16px;background:#f8fafc;border-radius:8px;vertical-align:top;">
                  <p style="margin:0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Complaint About (HR Staff)</p>
                  <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:#dc2626;">{complaint_target}</p>
                </td>
                <td width="16"></td>
                <td width="50%" style="padding:12px 16px;background:#f8fafc;border-radius:8px;vertical-align:top;">
                  <p style="margin:0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Severity Level</p>
                  <p style="margin:4px 0 0;font-size:16px;font-weight:700;color:{color};">{severity_upper}</p>
                </td>
              </tr>
              <tr><td height="8"></td></tr>
              <tr>
                <td width="50%" style="padding:12px 16px;background:#f8fafc;border-radius:8px;vertical-align:top;">
                  {ticket_row}
                </td>
                <td width="16"></td>
                <td width="50%" style="padding:12px 16px;background:#f8fafc;border-radius:8px;vertical-align:top;">
                  <p style="margin:0;font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Reported At</p>
                  <p style="margin:4px 0 0;font-size:14px;font-weight:600;color:#1e293b;">{now}</p>
                </td>
              </tr>
              {'<tr><td height="8"></td></tr><tr><td colspan="3" style="padding:12px 16px;background:#f8fafc;border-radius:8px;">' + reporter_row + '</td></tr>' if reporter_row else ''}
            </table>
            <div style="background:#fef2f2;border-radius:8px;padding:16px 20px;margin-bottom:24px;">
              <p style="margin:0;font-size:13px;color:#7f1d1d;">
                <strong>Action Required:</strong> Review this complaint in the admin dashboard.
                The employee's identity is set to <strong>confidential</strong> and is visible only to you.
                HR staff have no access to this ticket.
              </p>
            </div>
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="center" style="padding:8px 0;">
                  <a href="{settings.frontend_url.rstrip('/')}/#/admin/tickets/{ticket_id if ticket_id else ''}" style="display:inline-block;background:linear-gradient(135deg,#dc2626,#9b1c1c);color:#ffffff;font-size:14px;font-weight:600;padding:12px 32px;border-radius:8px;text-decoration:none;">Review in Admin Dashboard &rarr;</a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;border-top:1px solid #e2e8f0;padding:20px 32px;">
            <p style="margin:0;font-size:12px;color:#94a3b8;text-align:center;">
              This is a <strong style="color:#dc2626;">confidential escalation</strong> from
              <strong style="color:#64748b;">Pulsee AI</strong>. Do not forward to HR staff.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""

    subject = f"🚨 CONFIDENTIAL — Complaint About HR Staff ({complaint_target}) — Admin Action Required"
    recipients = _get_notification_recipients(role="higher_authority", severity=severity)
    if not recipients:
        logger.warning("No Authority recipients found for HR-conflict escalation")
        return {"status": "skipped", "reason": "no recipients"}

    notif_title = f"🚨 HR Conflict: Complaint about {complaint_target}"
    notif_message = f"Confidential complaint targeting HR staff ({complaint_target}). {complaint_summary[:200]}"

    logger.info(
        f"Notifying authority ({', '.join(r.email for r in recipients)}) about HR-targeted complaint "
        f"target='{complaint_target}' severity={severity}"
    )
    return _notify_recipients(
        recipients=recipients,
        subject=subject,
        body=body,
        notif_type="escalation",
        notif_title=notif_title,
        notif_message=notif_message,
        severity=severity,
        ticket_id=ticket_id,
    )


def notify_authority(complaint_summary: str, severity: str, ticket_id: str | None = None) -> dict:
    """Alert Higher Authority about a critical/high SLA breach.

    Sends email + in-app notification to all higher_authority users
    whose notification_levels include this severity.
    """
    subject = f"🚨 ESCALATION — {severity.upper()} SLA Breach Requires Immediate Attention"
    body = _build_html_email(complaint_summary, severity, ticket_id=ticket_id or "", role="higher_authority")

    recipients = _get_notification_recipients(role="higher_authority", severity=severity)
    if not recipients:
        logger.warning("No Authority notification recipients found — skipping")
        return {"status": "skipped", "reason": "no recipients"}

    notif_title = f"🚨 SLA Breach — {severity.upper()}"
    notif_message = f"SLA breach escalation: {complaint_summary[:200]}"

    logger.info(f"Notifying Authority ({', '.join(r.email for r in recipients)}) — severity={severity}")

    return _notify_recipients(
        recipients=recipients,
        subject=subject,
        body=body,
        notif_type="escalation",
        notif_title=notif_title,
        notif_message=notif_message,
        severity=severity,
        ticket_id=ticket_id,
    )
