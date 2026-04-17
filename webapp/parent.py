from io import BytesIO
from datetime import datetime
from urllib.parse import quote
from flask import Blueprint, flash, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from .extensions import db
from .models import (
    ActivityLog,
    LogoutRequest,
    MessageRecord,
    NotificationIngestionDevice,
    SafetyResourceDocument,
    User,
)
from .services.audit import log_event
from .services.family_context import get_selected_child, set_selected_child
from .services.notification_devices import issue_ingestion_token
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
    selected_child, children = get_selected_child(current_user.family_id)
    linked_devices = (
        NotificationIngestionDevice.query.filter_by(
            family_id=current_user.family_id,
            child_user_id=selected_child.id if selected_child else None,
        )
        .order_by(NotificationIngestionDevice.created_at.desc())
        .all()
    )
    messages = (
        MessageRecord.query.filter_by(
            family_id=current_user.family_id,
            submitted_by_id=selected_child.id if selected_child else None,
        )
        .order_by(MessageRecord.created_at.desc())
        .limit(15)
        .all()
    )
    logout_requests = (
        LogoutRequest.query.filter_by(
            family_id=current_user.family_id,
            child_user_id=selected_child.id if selected_child else None,
            status="pending",
        )
        .order_by(LogoutRequest.created_at.desc())
        .all()
    )
    activity_logs = (
        ActivityLog.query.filter(ActivityLog.family_id == current_user.family_id)
        .filter(
            or_(
                ActivityLog.subject_user_id == (selected_child.id if selected_child else None),
                ActivityLog.actor_id == (selected_child.id if selected_child else None),
            )
        )
        .order_by(ActivityLog.created_at.desc())
        .limit(20)
        .all()
    )
    approval_history = (
        LogoutRequest.query.filter_by(
            family_id=current_user.family_id,
            child_user_id=selected_child.id if selected_child else None,
        )
        .order_by(LogoutRequest.created_at.desc())
        .limit(12)
        .all()
    )
    safety_documents = (
        SafetyResourceDocument.query.filter_by(family_id=current_user.family_id)
        .order_by(SafetyResourceDocument.created_at.desc())
        .all()
    )
    logout_request_logs = (
        ActivityLog.query.filter_by(
            family_id=current_user.family_id,
            event_type="logout_requested",
            subject_user_id=selected_child.id if selected_child else None,
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
                    logout_request.action_description
                    or detail_log.details
                    if detail_log
                    else logout_request.action_description
                    or "Child requested sign-out from this device."
                ),
                "request_note": logout_request.request_note,
                "requested_at": logout_request.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        )

    high_risk_count = sum(1 for message in messages if message.predicted_label != "safe")
    reviewed_count = sum(1 for message in messages if message.reviewed_label)
    alert_count = high_risk_count + len(logout_requests)
    latest_sync = activity_logs[0].created_at.strftime("%Y-%m-%d %H:%M") if activity_logs else "No sync yet"
    pending_android_link = None
    if selected_child:
        flash_child_id = session.get("android_link_child_id")
        if flash_child_id == selected_child.id:
            pairing_uri = (
                "cybermzazi://pair"
                f"?base_url={quote(request.url_root.rstrip('/'), safe='')}"
                f"&token={quote(session.get('android_link_token') or '', safe='')}"
                f"&device_name={quote(session.get('android_link_device_name') or '', safe='')}"
            )
            pending_android_link = {
                "device_name": session.get("android_link_device_name"),
                "ingest_token": session.get("android_link_token"),
                "endpoint_hint": "/api/device-ingest/android-notifications",
                "pairing_uri": pairing_uri,
                "qr_image_url": (
                    "https://api.qrserver.com/v1/create-qr-code/?size=220x220&data="
                    f"{quote(pairing_uri, safe='')}"
                ),
            }
            session.pop("android_link_child_id", None)
            session.pop("android_link_device_name", None)
            session.pop("android_link_token", None)
    return {
        "children": children,
        "selected_child": selected_child,
        "linked_devices": linked_devices,
        "pending_android_link": pending_android_link,
        "messages": messages,
        "logout_requests": logout_requests,
        "logout_request_cards": logout_request_cards,
        "selected_logout_request": logout_request_cards[0] if logout_request_cards else None,
        "activity_logs": activity_logs,
        "approval_history": approval_history,
        "safety_documents": safety_documents,
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


@parent_bp.post("/select-child")
def select_child():
    child_id = request.form.get("child_id", type=int)
    child = set_selected_child(current_user.family_id, child_id or 0)
    if child is None:
        flash("Choose a valid child profile.", "warning")
    else:
        flash(f"{child.name} selected.", "success")
    return redirect(request.form.get("next") or url_for("parent.dashboard"))


@parent_bp.post("/family-hub/children")
def add_child():
    child_name = request.form.get("child_name", "").strip()
    child_username = request.form.get("child_username", "").strip()
    child_password = request.form.get("child_password", "")
    preferred_language = request.form.get("preferred_language", "en").strip().lower()

    if not all([child_name, child_username, child_password]):
        flash("Fill in all child fields.", "warning")
        return redirect(url_for("parent.family_hub"))
    if preferred_language not in SUPPORTED_LANGUAGES:
        preferred_language = "en"
    if User.query.filter_by(username=child_username).first():
        flash("That child username is already in use.", "danger")
        return redirect(url_for("parent.family_hub"))

    child_user = User(
        family_id=current_user.family_id,
        role="child",
        name=child_name,
        username=child_username,
        logout_requires_parent_approval=True,
        preferred_language=preferred_language,
    )
    child_user.set_password(child_password)
    db.session.add(child_user)
    db.session.flush()
    set_selected_child(current_user.family_id, child_user.id)
    log_event(
        current_user.family_id,
        current_user.id,
        "child_added",
        f"Added child profile {child_name}",
        subject_user_id=child_user.id,
    )
    db.session.commit()
    flash("Child profile added.", "success")
    return redirect(url_for("parent.family_hub"))


@parent_bp.post("/language")
def set_language():
    language = request.form.get("language", "en").strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        flash("Choose English or Swahili.", "warning")
        return redirect(url_for("parent.language_settings"))

    session["ui_language"] = language
    current_user.preferred_language = language
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
    uploads = [upload for upload in request.files.getlist("attachments") if upload and upload.filename]
    if not uploads:
        flash("Choose one or more documents first.", "warning")
        return redirect(url_for("parent.safety_resources"))

    saved_names = []
    for upload in uploads:
        binary_data = upload.read()
        document = SafetyResourceDocument(
            family_id=current_user.family_id,
            uploaded_by_id=current_user.id,
            filename=upload.filename,
            content_type=upload.mimetype,
            file_size=len(binary_data),
            binary_data=binary_data,
        )
        db.session.add(document)
        saved_names.append(upload.filename)

    log_event(
        current_user.family_id,
        current_user.id,
        "resource_attachment_added",
        f"Uploaded safety resource documents: {', '.join(saved_names)}",
    )
    db.session.commit()
    flash("Safety resource documents uploaded.", "success")
    return redirect(url_for("parent.safety_resources"))


@parent_bp.post("/android-devices")
def create_android_device():
    selected_child, _children = get_selected_child(current_user.family_id)
    child_user_id = request.form.get("child_user_id", type=int) or (selected_child.id if selected_child else 0)
    device_name = request.form.get("device_name", "").strip()
    if not child_user_id:
        flash("Select a child profile first.", "warning")
        return redirect(url_for("parent.child_profile"))
    if not device_name:
        flash("Enter an Android device name first.", "warning")
        return redirect(url_for("parent.child_profile"))

    child_user = User.query.filter_by(
        id=child_user_id,
        family_id=current_user.family_id,
        role="child",
    ).first()
    if child_user is None:
        flash("Child profile not found.", "danger")
        return redirect(url_for("parent.child_profile"))

    ingest_token = issue_ingestion_token()
    device = NotificationIngestionDevice(
        family_id=current_user.family_id,
        child_user_id=child_user.id,
        device_name=device_name,
        platform="android",
        permission_scope="notification_listener",
        token_hash=NotificationIngestionDevice.hash_token(ingest_token),
        status="active",
    )
    db.session.add(device)
    db.session.flush()
    log_event(
        current_user.family_id,
        current_user.id,
        "android_device_link_created",
        f"Created Android notification link '{device_name}' for {child_user.name}",
        subject_user_id=child_user.id,
    )
    db.session.commit()
    session["android_link_child_id"] = child_user.id
    session["android_link_device_name"] = device_name
    session["android_link_token"] = ingest_token
    flash("Android notification link created. Copy the token below into the Android app.", "success")
    return redirect(request.form.get("next") or url_for("parent.child_profile"))


@parent_bp.post("/android-devices/<int:device_id>/disable")
def disable_android_device(device_id: int):
    device = NotificationIngestionDevice.query.filter_by(
        id=device_id,
        family_id=current_user.family_id,
    ).first_or_404()
    device.status = "disabled"
    log_event(
        current_user.family_id,
        current_user.id,
        "android_device_link_disabled",
        f"Disabled Android notification link '{device.device_name}'",
        subject_user_id=device.child_user_id,
    )
    db.session.commit()
    flash("Android notification link disabled.", "success")
    return redirect(request.form.get("next") or url_for("parent.child_profile"))


@parent_bp.get("/safety-resources/documents/<int:document_id>")
def download_resource_document(document_id: int):
    document = SafetyResourceDocument.query.filter_by(
        id=document_id, family_id=current_user.family_id
    ).first_or_404()
    return send_file(
        BytesIO(document.binary_data),
        mimetype=document.content_type or "application/octet-stream",
        as_attachment=True,
        download_name=document.filename,
    )


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
        subject_user_id=record.submitted_by_id,
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
        subject_user_id=logout_request.child_user_id,
    )
    db.session.commit()
    flash("Logout approved. The child can now sign out once.", "success")
    return redirect(url_for("parent.alerts"))
