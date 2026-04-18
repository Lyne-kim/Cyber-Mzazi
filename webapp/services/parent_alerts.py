from __future__ import annotations

import smtplib
from email.message import EmailMessage

from flask import current_app, has_request_context, url_for

from ..models import LogoutRequest, MessageRecord, User


def _can_send_parent_alerts(parent_user: User | None) -> bool:
    return bool(
        parent_user
        and parent_user.email
        and parent_user.email_verified
        and current_app.config.get("ALERT_EMAIL_ENABLED", True)
        and current_app.config.get("MAIL_SERVER")
        and current_app.config.get("MAIL_DEFAULT_SENDER")
    )


def _alerts_url() -> str:
    if has_request_context():
        path = url_for("parent.alerts")
    else:
        with current_app.test_request_context():
            path = url_for("parent.alerts")
    app_base_url = current_app.config.get("APP_BASE_URL", "")
    if app_base_url:
        return f"{app_base_url}{path}"
    return path


def _send_email(recipient: str, subject: str, body: str) -> tuple[bool, str]:
    sender = current_app.config["MAIL_DEFAULT_SENDER"]
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)

    server = current_app.config["MAIL_SERVER"]
    port = current_app.config["MAIL_PORT"]
    username = current_app.config["MAIL_USERNAME"]
    password = current_app.config["MAIL_PASSWORD"]
    use_tls = current_app.config["MAIL_USE_TLS"]
    use_ssl = current_app.config["MAIL_USE_SSL"]

    try:
        if use_ssl:
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(server, port, timeout=20)
        else:
            smtp = smtplib.SMTP(server, port, timeout=20)
        with smtp:
            if use_tls and not use_ssl:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except Exception as exc:  # pragma: no cover - network dependent
        return False, f"Parent alert email could not be sent: {exc}"
    return True, "Parent alert email sent."


def send_high_risk_message_alert(parent_user: User | None, child_user: User | None, record: MessageRecord) -> tuple[bool, str]:
    if record.predicted_label == "safe":
        return False, "Message was classified as safe."
    if not _can_send_parent_alerts(parent_user):
        return False, "Parent alert email delivery is not configured."

    child_name = child_user.name if child_user else "your child"
    body = (
        f"Hello {parent_user.name},\n\n"
        f"Cyber Mzazi detected a high-risk message for {child_name}.\n\n"
        f"Threat type: {record.predicted_label.title()}\n"
        f"Source platform: {record.source_platform.title()}\n"
        f"Sender handle: {record.sender_handle or 'Unknown handle'}\n"
        f"Confidence: {record.predicted_confidence:.0%}\n"
        f"Indicators: {record.risk_indicators or 'Not provided'}\n\n"
        f"Message excerpt:\n{(record.message_text or '')[:500]}\n\n"
        f"Review the alert here:\n{_alerts_url()}\n"
    )
    subject = f"Cyber Mzazi alert: {record.predicted_label.title()} detected"
    return _send_email(parent_user.email, subject, body)


def send_logout_request_alert(parent_user: User | None, child_user: User | None, logout_request: LogoutRequest) -> tuple[bool, str]:
    if not _can_send_parent_alerts(parent_user):
        return False, "Parent alert email delivery is not configured."

    child_name = child_user.name if child_user else "your child"
    note = f"\nNote from child device: {logout_request.request_note}\n" if logout_request.request_note else "\n"
    body = (
        f"Hello {parent_user.name},\n\n"
        f"{child_name} requested sign-out from a child device.\n"
        "Approval is required before that child session can log out.\n"
        f"{note}\n"
        f"Review the request here:\n{_alerts_url()}\n"
    )
    subject = "Cyber Mzazi alert: child logout approval needed"
    return _send_email(parent_user.email, subject, body)
