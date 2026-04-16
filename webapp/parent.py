from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import ActivityLog, LogoutRequest, MessageRecord
from .services.audit import log_event
from .ui_text import SUPPORTED_LANGUAGES


parent_bp = Blueprint("parent", __name__, url_prefix="/parent")


PARENT_NAV_ITEMS = [
    {"endpoint": "parent.alerts", "icon": "&#128680;", "label": "Alerts", "key": "alerts"},
    {"endpoint": "parent.dashboard", "icon": "&#128202;", "label": "Dashboard", "key": "dashboard"},
    {"endpoint": "parent.child_profile", "icon": "&#128100;", "label": "Child Profile", "key": "child_profile"},
    {"endpoint": "parent.activity_log", "icon": "&#128203;", "label": "Activity Log", "key": "activity_log"},
    {"endpoint": "parent.alert_settings", "icon": "&#9881;", "label": "Alert Settings", "key": "alert_settings"},
]

PARENT_SUPPORT_ITEMS = [
    {"endpoint": "parent.family_hub", "icon": "&#128106;", "label": "Family Hub", "key": "family_hub"},
    {"endpoint": "parent.safety_resources", "icon": "&#128218;", "label": "Safety Resources", "key": "safety_resources"},
    {"endpoint": "parent.help_support", "icon": "&#10067;", "label": "Help & Support", "key": "help_support"},
    {"endpoint": "parent.privacy_center", "icon": "&#128196;", "label": "Privacy Center", "key": "privacy_center"},
    {"endpoint": "parent.system_status", "icon": "&#128257;", "label": "System Status", "key": "system_status"},
]

PARENT_ADVANCED_ITEMS = [
    {"endpoint": "parent.insights", "icon": "&#128200;", "label": "Insights", "key": "insights"},
    {"endpoint": "parent.language_settings", "icon": "&#127760;", "label": "Language", "key": "language_settings"},
    {"endpoint": "parent.notification_log", "icon": "&#128276;", "label": "Notification Log", "key": "notification_log"},
    {"endpoint": "parent.trusted_contacts", "icon": "&#129309;", "label": "Trusted Contacts", "key": "trusted_contacts"},
]


@parent_bp.before_request
@login_required
def require_parent():
    if current_user.role != "parent":
        flash("Parent access only.", "danger")
        return redirect(url_for("child.dashboard"))
    return None


def _parent_data() -> dict:
    messages = (
        MessageRecord.query.filter_by(family_id=current_user.family_id)
        .order_by(MessageRecord.created_at.desc())
        .limit(15)
        .all()
    )
    logout_requests = (
        LogoutRequest.query.filter_by(family_id=current_user.family_id, status="pending")
        .order_by(LogoutRequest.created_at.desc())
        .all()
    )
    activity_logs = (
        ActivityLog.query.filter_by(family_id=current_user.family_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(20)
        .all()
    )
    logout_request_logs = (
        ActivityLog.query.filter_by(
            family_id=current_user.family_id, event_type="logout_requested"
        )
        .order_by(ActivityLog.created_at.desc())
        .all()
    )
    logout_details_by_child: dict[int, ActivityLog] = {}
    for log in logout_request_logs:
        if log.actor_id and log.actor_id not in logout_details_by_child:
            logout_details_by_child[log.actor_id] = log

    logout_request_cards = []
    for logout_request in logout_requests:
        detail_log = logout_details_by_child.get(logout_request.child_user_id)
        logout_request_cards.append(
            {
                "request": logout_request,
                "detail": (
                    detail_log.details
                    if detail_log
                    else "Child requested sign-out from this device."
                ),
                "requested_at": logout_request.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        )

    high_risk_count = sum(1 for message in messages if message.predicted_label != "safe")
    reviewed_count = sum(1 for message in messages if message.reviewed_label)
    alert_count = high_risk_count + len(logout_requests)
    latest_sync = activity_logs[0].created_at.strftime("%Y-%m-%d %H:%M") if activity_logs else "No sync yet"
    return {
        "messages": messages,
        "logout_requests": logout_requests,
        "logout_request_cards": logout_request_cards,
        "selected_logout_request": logout_request_cards[0] if logout_request_cards else None,
        "activity_logs": activity_logs,
        "high_risk_count": high_risk_count,
        "reviewed_count": reviewed_count,
        "alert_count": alert_count,
        "latest_sync": latest_sync,
    }


def _render_parent_page(page_key: str, page_title: str) -> str:
    context = _parent_data()
    return render_template(
        "parent_page.html",
        page_key=page_key,
        page_title=page_title,
        primary_nav_items=PARENT_NAV_ITEMS,
        support_nav_items=PARENT_SUPPORT_ITEMS,
        advanced_nav_items=PARENT_ADVANCED_ITEMS,
        **context,
    )


@parent_bp.route("/dashboard")
def dashboard():
    return _render_parent_page("dashboard", "Dashboard")


@parent_bp.route("/alerts")
def alerts():
    return _render_parent_page("alerts", "Alerts")


@parent_bp.route("/child-profile")
def child_profile():
    return _render_parent_page("child_profile", "Child Profile")


@parent_bp.route("/activity-log")
def activity_log():
    return _render_parent_page("activity_log", "Activity Log")


@parent_bp.route("/alert-settings")
def alert_settings():
    return _render_parent_page("alert_settings", "Alert Settings")


@parent_bp.route("/family-hub")
def family_hub():
    return _render_parent_page("family_hub", "Family Hub")


@parent_bp.route("/safety-resources")
def safety_resources():
    return _render_parent_page("safety_resources", "Safety Resources")


@parent_bp.route("/help-support")
def help_support():
    return _render_parent_page("help_support", "Help & Support")


@parent_bp.route("/privacy-center")
def privacy_center():
    return _render_parent_page("privacy_center", "Privacy Center")


@parent_bp.route("/system-status")
def system_status():
    return _render_parent_page("system_status", "System Status")


@parent_bp.route("/insights")
def insights():
    return _render_parent_page("insights", "Insights")


@parent_bp.route("/language-settings")
def language_settings():
    return _render_parent_page("language_settings", "Language Settings")


@parent_bp.route("/notification-log")
def notification_log():
    return _render_parent_page("notification_log", "Notification Log")


@parent_bp.route("/trusted-contacts")
def trusted_contacts():
    return _render_parent_page("trusted_contacts", "Trusted Contacts")


@parent_bp.post("/language")
def set_language():
    language = request.form.get("language", "en").strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        flash("Choose English or Swahili.", "warning")
        return redirect(url_for("parent.language_settings"))

    session["ui_language"] = language
    log_event(
        current_user.family_id,
        current_user.id,
        "language_changed",
        f"Parent interface language set to {SUPPORTED_LANGUAGES[language]}",
    )
    db.session.commit()
    flash(f"Language updated to {SUPPORTED_LANGUAGES[language]}.", "success")
    return redirect(request.form.get("next") or url_for("parent.language_settings"))


@parent_bp.post("/safety-resources/attachments")
def attach_resource_documents():
    files = [
        upload.filename
        for upload in request.files.getlist("attachments")
        if upload and upload.filename
    ]
    if not files:
        flash("Choose one or more documents first.", "warning")
        return redirect(url_for("parent.safety_resources"))

    log_event(
        current_user.family_id,
        current_user.id,
        "resource_attachment_added",
        f"Safety resource placeholders added for: {', '.join(files)}",
    )
    db.session.commit()
    flash("Document placeholders added to safety resources.", "success")
    return redirect(url_for("parent.safety_resources"))


@parent_bp.post("/messages/<int:message_id>/review")
def review_message(message_id: int):
    record = MessageRecord.query.filter_by(
        id=message_id, family_id=current_user.family_id
    ).first_or_404()
    reviewed_label = request.form.get("reviewed_label", "").strip()
    if not reviewed_label:
        flash("Choose a reviewed label.", "warning")
        return redirect(url_for("parent.alerts"))

    record.reviewed_label = reviewed_label
    record.reviewed_by_id = current_user.id
    log_event(
        current_user.family_id,
        current_user.id,
        "message_reviewed",
        f"Message {record.id} reviewed as {reviewed_label}",
    )
    db.session.commit()
    flash("Review saved. You can use reviewed labels for later retraining.", "success")
    return redirect(url_for("parent.alerts"))


@parent_bp.post("/logout-requests/<int:request_id>/approve")
def approve_logout(request_id: int):
    logout_request = LogoutRequest.query.filter_by(
        id=request_id, family_id=current_user.family_id, status="pending"
    ).first_or_404()
    logout_request.status = "approved"
    logout_request.resolved_by_id = current_user.id
    logout_request.resolved_at = datetime.utcnow()
    log_event(
        current_user.family_id,
        current_user.id,
        "logout_approved",
        f"Approved sign-out for child user {logout_request.child_user_id}. The child device can close the current child session once.",
    )
    db.session.commit()
    flash("Logout approved. The child can now sign out once.", "success")
    return redirect(url_for("parent.alerts"))
