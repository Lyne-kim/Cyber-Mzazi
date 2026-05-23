from __future__ import annotations

from flask import current_app, url_for

from ..models import SafetyResourceRequest, User
from .mail_delivery import is_mail_delivery_configured, send_email


def notify_developer_resource_request(
    resource_request: SafetyResourceRequest,
    requested_by: User,
) -> tuple[bool, str]:
    recipient = str(current_app.config.get("DEVELOPER_NOTIFICATION_EMAIL", "")).strip()
    if not recipient:
        return False, "Developer notification email is not configured."
    if not is_mail_delivery_configured():
        return False, "Mail delivery is not configured."

    base_url = str(current_app.config.get("APP_BASE_URL", "")).rstrip("/")
    developer_path = url_for("developer.dashboard")
    developer_url = f"{base_url}{developer_path}" if base_url else developer_path
    subject = f"Cyber Mzazi resource request: {resource_request.title}"
    body = "\n".join(
        [
            "A parent/guardian requested a safety resource.",
            "",
            f"Title/topic: {resource_request.title}",
            f"Topic: {resource_request.topic}",
            f"Audience: {resource_request.audience}",
            f"Suggested URL: {resource_request.suggested_url or 'Not provided'}",
            f"Parent/guardian: {requested_by.name} ({requested_by.display_identifier})",
            "",
            "Note:",
            resource_request.note or "No note provided.",
            "",
            f"Review it in the developer console: {developer_url}",
        ]
    )
    return send_email(recipient, subject, body)
