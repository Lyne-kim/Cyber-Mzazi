from datetime import datetime
from io import BytesIO
from types import SimpleNamespace
from urllib.parse import quote
from urllib.parse import urlparse
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required, logout_user
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from ml.labels import RISK_TERMS, SAFE_LABEL, SUPPORTED_LABELS, label_summary_rows, label_title, normalize_label

from .extensions import db
from .models import (
    ActivityLog,
    LogoutRequest,
    MessageRecord,
    NotificationIngestionDevice,
    SafetyResourceDocument,
    SafetyResourceLink,
    User,
)
from .services.audit import log_event
from .services.family_context import get_selected_child, set_selected_child
from .services.notification_devices import issue_ingestion_token
from .services.review_feedback import build_review_signature
from .services.safety_assistant import build_safety_assistant_response
from .ui_text import SUPPORTED_LANGUAGES


parent_bp = Blueprint("parent", __name__, url_prefix="/parent")

MAX_RESOURCE_ATTACHMENT_BYTES = 8 * 1024 * 1024


PARENT_NAV_ITEMS = [
    {"endpoint": "parent.alerts", "icon": "&#128681;", "label": "Alerts", "key": "alerts"},
    {"endpoint": "parent.dashboard", "icon": "&#128202;", "label": "Dashboard", "key": "dashboard"},
    {"endpoint": "parent.child_profile", "icon": "&#128100;", "label": "Child Profile", "key": "child_profile"},
    {"endpoint": "parent.activity_log", "icon": "&#128203;", "label": "Activity Log", "key": "activity_log"},
    {"endpoint": "parent.alert_settings", "icon": "&#9881;", "label": "Alert Settings", "key": "alert_settings"},
]

PARENT_SUPPORT_ITEMS = [
    {"endpoint": "parent.family_hub", "icon": "&#128106;", "label": "Family Hub", "key": "family_hub"},
    {"endpoint": "parent.safety_resources", "icon": "&#128218;", "label": "Safety Resources", "key": "safety_resources"},
    {"endpoint": "parent.ai_assistant", "icon": "&#129302;", "label": "AI Assistant", "key": "ai_assistant"},
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


def _alert_session_key(selected_child_id: int | None) -> str:
    child_key = selected_child_id if selected_child_id is not None else "all"
    return f"parent_alert_seen:{current_user.family_id}:{child_key}"


def _latest_alert_key(notification_items: list[dict]) -> str:
    return notification_items[0]["key"] if notification_items else ""


def _resolve_logout_request(logout_request: LogoutRequest, status: str) -> None:
    logout_request.status = status
    logout_request.resolved_by_id = current_user.id
    logout_request.resolved_at = datetime.utcnow()
    db.session.add(logout_request)


def _mark_alerts_seen(selected_child_id: int | None, notification_items: list[dict]) -> None:
    latest_key = _latest_alert_key(notification_items)
    session[_alert_session_key(selected_child_id)] = latest_key
    session.modified = True


def _unread_alert_count(selected_child_id: int | None, notification_items: list[dict]) -> int:
    seen_key = session.get(_alert_session_key(selected_child_id), "")
    if not notification_items:
        return 0
    if not seen_key:
        return len(notification_items)

    unread = 0
    for item in notification_items:
        if item["key"] == seen_key:
            break
        unread += 1
    return unread


def _build_notification_items(selected_child, messages, logout_requests) -> list[dict]:
    notifications: list[dict] = []
    child_name = selected_child.name if selected_child else "your child"

    for logout_request in logout_requests:
        notifications.append(
            {
                "key": f"logout-request-{logout_request.id}",
                "type": "logout_request",
                "severity": "warning",
                "title": "Child logout approval needed",
                "body": (
                    f"{child_name} requested sign-out on a child device. "
                    "Open Alerts to review and approve the request."
                ),
                "created_at": logout_request.created_at.isoformat(),
                "created_at_label": logout_request.created_at.strftime("%Y-%m-%d %H:%M"),
                "target_url": url_for("parent.alerts"),
                "child_name": child_name,
            }
        )

    for message in messages:
        if message.predicted_label == "safe":
            continue
        notifications.append(
            {
                "key": f"message-alert-{message.id}",
                "type": "message_alert",
                "severity": "danger",
                "title": f"{label_title(message.predicted_label)} alert detected",
                "body": (
                    f"Cyber Mzazi flagged a third-party message for {child_name} "
                    f"from {message.source_platform.title()}."
                ),
                "created_at": message.created_at.isoformat(),
                "created_at_label": message.created_at.strftime("%Y-%m-%d %H:%M"),
                "target_url": url_for("parent.alerts"),
                "child_name": child_name,
                "message_excerpt": (message.message_text or "")[:140],
            }
        )

    notifications.sort(key=lambda item: item["created_at"], reverse=True)
    return notifications


def _message_dashboard_view(message: MessageRecord) -> SimpleNamespace:
    raw_label = str(message.predicted_label or "").strip().lower()
    normalized_label = normalize_label(raw_label)
    risk_indicators = message.risk_indicators
    verification_label = normalize_label(message.verification_label, default="") if message.verification_label else None
    confidence = float(message.predicted_confidence or 0.0)
    lowered = str(message.message_text or "").lower()
    commerce_terms = {
        "offer",
        "offers",
        "sale",
        "discount",
        "shop",
        "shopping",
        "dress",
        "wallet",
        "deodorant",
        "delivery",
        "cart",
        "order",
        "promo",
        "kilimall",
        "jumia",
    }
    if (
        normalized_label != SAFE_LABEL
        and confidence < 0.78
        and any(term in lowered for term in commerce_terms)
    ):
        normalized_label = SAFE_LABEL
        confidence = max(confidence, 0.72)
        risk_indicators = ",".join(RISK_TERMS[SAFE_LABEL])
        verification_label = SAFE_LABEL

    return SimpleNamespace(
        id=message.id,
        family_id=message.family_id,
        submitted_by_id=message.submitted_by_id,
        source_platform=message.source_platform,
        sender_handle=message.sender_handle,
        message_text=message.message_text,
        capture_method=message.capture_method,
        notification_title=message.notification_title,
        source_app_package=message.source_app_package,
        predicted_label=normalized_label,
        predicted_confidence=confidence,
        risk_indicators=risk_indicators,
        verification_status=message.verification_status,
        verification_label=verification_label,
        verification_confidence=message.verification_confidence,
        verification_notes=message.verification_notes,
        reviewed_label=normalize_label(message.reviewed_label, default="") if message.reviewed_label else None,
        reviewed_by_id=message.reviewed_by_id,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


@parent_bp.before_request
@login_required
def require_parent():
    if current_user.role != "parent":
        flash("Parent access only.", "danger")
        return redirect(url_for("child.dashboard"))
    if not current_user.can_log_in:
        pending_identifier = current_user.email or current_user.phone or ""
        logout_user()
        flash("Verify the parent account before continuing.", "warning")
        return redirect(url_for("auth.parent_login", pending_identifier=pending_identifier))
    return None


def _device_sync_summary(devices: list[NotificationIngestionDevice]) -> dict[str, str]:
    active_devices = [device for device in devices if device.status == "active"]
    if not active_devices:
        return {"label": "No device linked", "tone": "offline"}

    latest_device = max(
        active_devices,
        key=lambda device: device.last_ingested_at or device.last_seen_at or device.created_at,
    )
    latest_contact = latest_device.last_ingested_at or latest_device.last_seen_at
    if latest_contact:
        return {
            "label": f"Device synced {latest_contact.strftime('%Y-%m-%d %H:%M')}",
            "tone": "online",
        }

    return {"label": "Device linked - waiting for sync", "tone": "pending"}


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
    raw_messages = (
        MessageRecord.query.filter_by(
            family_id=current_user.family_id,
            submitted_by_id=selected_child.id if selected_child else None,
        )
        .order_by(MessageRecord.created_at.desc())
        .limit(15)
        .all()
    )
    messages = [_message_dashboard_view(message) for message in raw_messages]
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
    safety_links = (
        SafetyResourceLink.query.filter_by(family_id=current_user.family_id)
        .order_by(SafetyResourceLink.created_at.desc())
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

    active_messages = [
        message
        for message in messages
        if message.predicted_label != "safe" and not message.reviewed_label
    ]
    high_risk_count = len(active_messages)
    reviewed_count = sum(1 for message in messages if message.reviewed_label)
    alert_count = high_risk_count + len(logout_requests)
    message_label_breakdown = label_summary_rows(
        [
            message.predicted_label
            for message in active_messages
            if message.predicted_label and message.predicted_label != "safe"
        ]
    )
    latest_sync = activity_logs[0].created_at.strftime("%Y-%m-%d %H:%M") if activity_logs else "No sync yet"
    notification_items = _build_notification_items(selected_child, active_messages, logout_requests)
    unread_alert_count = _unread_alert_count(
        selected_child.id if selected_child else None,
        notification_items,
    )
    pending_android_link = None
    android_download = None
    download_url = current_app.config.get("ANDROID_COMPANION_DOWNLOAD_URL", "").strip()
    if download_url:
        android_download = {
            "url": download_url,
            "qr_image_url": (
                "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data="
                f"{quote(download_url, safe='')}"
            ),
        }
    if selected_child:
        flash_child_id = session.get("android_link_child_id")
        if flash_child_id == selected_child.id:
            pairing_uri = (
                "cybermzazi://pair"
                f"?base_url={quote(request.url_root.rstrip('/'), safe='')}"
                f"&token={quote(session.get('android_link_token') or '', safe='')}"
                f"&device_name={quote(session.get('android_link_device_name') or '', safe='')}"
                "&role=child"
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
        "android_download": android_download,
        "device_sync": _device_sync_summary(linked_devices),
        "messages": messages,
        "active_messages": active_messages,
        "logout_requests": logout_requests,
        "logout_request_cards": logout_request_cards,
        "selected_logout_request": logout_request_cards[0] if logout_request_cards else None,
        "activity_logs": activity_logs,
        "approval_history": approval_history,
        "safety_documents": safety_documents,
        "safety_links": safety_links,
        "high_risk_count": high_risk_count,
        "reviewed_count": reviewed_count,
        "alert_count": alert_count,
        "unread_alert_count": unread_alert_count,
        "message_label_breakdown": message_label_breakdown,
        "latest_sync": latest_sync,
        "notification_items": notification_items,
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


@parent_bp.get("/notification-feed")
def notification_feed():
    context = _parent_data()
    return jsonify(
        {
            "ok": True,
            "alert_count": context["alert_count"],
            "unread_alert_count": context["unread_alert_count"],
            "notification_items": context["notification_items"],
        }
    )


@parent_bp.route("/alerts")
def alerts():
    context = _parent_data()
    selected_child = context["selected_child"]
    _mark_alerts_seen(selected_child.id if selected_child else None, context["notification_items"])
    context["unread_alert_count"] = 0
    return render_template(
        "parent_page.html",
        page_key="alerts",
        page_title="Alerts",
        primary_nav_items=PARENT_NAV_ITEMS,
        support_nav_items=PARENT_SUPPORT_ITEMS,
        advanced_nav_items=PARENT_ADVANCED_ITEMS,
        **context,
    )


@parent_bp.post("/alerts/mark-seen")
def mark_alerts_seen():
    context = _parent_data()
    selected_child = context["selected_child"]
    _mark_alerts_seen(selected_child.id if selected_child else None, context["notification_items"])
    return jsonify({"ok": True, "unread_alert_count": 0})


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


@parent_bp.route("/ai-assistant", methods=["GET", "POST"])
def ai_assistant():
    assistant_result = None
    assistant_prompt = ""
    assistant_history = session.get("parent_assistant_history", [])
    if not isinstance(assistant_history, list):
        assistant_history = []
    if request.method == "POST":
        assistant_prompt = request.form.get("assistant_prompt", "").strip()
        assistant_result = build_safety_assistant_response(
            assistant_prompt,
            audience="parent",
            family_id=current_user.family_id,
        )
        if not assistant_result.get("ok"):
            flash(assistant_result.get("error", "Assistant could not analyse that yet."), "danger")
        else:
            assistant_history.append(
                {
                    "user": assistant_prompt,
                    "assistant": assistant_result.get("assistant_message") or assistant_result.get("explanation"),
                    "risk_level": assistant_result.get("risk_level"),
                    "label_title": assistant_result.get("label_title"),
                }
            )
            session["parent_assistant_history"] = assistant_history[-8:]
    context = _parent_data()
    return render_template(
        "parent_page.html",
        page_key="ai_assistant",
        page_title="AI Assistant",
        primary_nav_items=PARENT_NAV_ITEMS,
        support_nav_items=PARENT_SUPPORT_ITEMS,
        advanced_nav_items=PARENT_ADVANCED_ITEMS,
        assistant_prompt=assistant_prompt,
        assistant_result=assistant_result,
        assistant_history=assistant_history,
        **context,
    )


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
    if User.query.filter_by(
        family_id=current_user.family_id,
        role="child",
        username=child_username,
    ).first():
        flash("That child username is already in use in this family.", "danger")
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
    try:
        for upload in uploads:
            binary_data = upload.read()
            if len(binary_data) > MAX_RESOURCE_ATTACHMENT_BYTES:
                flash(
                    f"{upload.filename} is too large. Upload files up to 8 MB each.",
                    "warning",
                )
                db.session.rollback()
                return redirect(url_for("parent.safety_resources"))
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
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Failed to save safety resource documents")
        flash(
            "Documents could not be uploaded right now. Try a smaller file or retry in a moment.",
            "danger",
        )
        return redirect(url_for("parent.safety_resources"))

    flash("Safety resource documents uploaded.", "success")
    return redirect(url_for("parent.safety_resources"))


@parent_bp.post("/safety-resources/links")
def add_resource_link():
    title = request.form.get("title", "").strip()
    url = request.form.get("url", "").strip()
    topic = request.form.get("topic", "").strip() or "Digital safety"
    audience = request.form.get("audience", "all").strip().lower()
    summary = request.form.get("summary", "").strip()

    parsed = urlparse(url)
    if not title or parsed.scheme not in {"http", "https"} or not parsed.netloc:
        flash("Enter a title and a valid https:// resource link.", "warning")
        return redirect(url_for("parent.safety_resources"))
    if audience not in {"all", "parent", "child"}:
        audience = "all"

    resource_link = SafetyResourceLink(
        family_id=current_user.family_id,
        created_by_id=current_user.id,
        title=title,
        url=url,
        topic=topic,
        audience=audience,
        summary=summary,
    )
    db.session.add(resource_link)
    log_event(
        current_user.family_id,
        current_user.id,
        "resource_link_added",
        f"Added safety resource link: {title}",
    )
    db.session.commit()
    flash("Safety resource link added.", "success")
    return redirect(url_for("parent.safety_resources"))


@parent_bp.post("/safety-resources/links/<int:link_id>/delete")
def delete_resource_link(link_id: int):
    resource_link = SafetyResourceLink.query.filter_by(
        id=link_id,
        family_id=current_user.family_id,
    ).first_or_404()
    db.session.delete(resource_link)
    log_event(
        current_user.family_id,
        current_user.id,
        "resource_link_deleted",
        f"Deleted safety resource link: {resource_link.title}",
    )
    db.session.commit()
    flash("Safety resource link removed.", "success")
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
    if reviewed_label not in SUPPORTED_LABELS:
        flash("Choose a valid reviewed label.", "warning")
        return redirect(url_for("parent.alerts"))

    record.reviewed_label = reviewed_label
    record.reviewed_by_id = current_user.id
    record.review_signature = build_review_signature(record.message_text)
    log_event(
        current_user.family_id,
        current_user.id,
        "message_reviewed",
        f"Message {record.id} reviewed as {reviewed_label}",
        subject_user_id=record.submitted_by_id,
    )
    db.session.commit()
    flash("Review saved. Future matching messages will now reuse this reviewed label.", "success")
    return redirect(url_for("parent.alerts"))


@parent_bp.post("/messages/<int:message_id>/delete")
def delete_message(message_id: int):
    record = MessageRecord.query.filter_by(
        id=message_id,
        family_id=current_user.family_id,
    ).first_or_404()
    subject_user_id = record.submitted_by_id
    db.session.delete(record)
    log_event(
        current_user.family_id,
        current_user.id,
        "message_deleted",
        f"Deleted alert/message {message_id}",
        subject_user_id=subject_user_id,
    )
    db.session.commit()
    flash("Alert deleted.", "success")
    return redirect(url_for("parent.alerts"))


@parent_bp.post("/messages/bulk-delete")
def bulk_delete_messages():
    message_ids = [
        int(message_id)
        for message_id in request.form.getlist("message_ids")
        if str(message_id).isdigit()
    ]
    if not message_ids:
        flash("Select at least one alert first.", "warning")
        return redirect(url_for("parent.alerts"))

    records = MessageRecord.query.filter(
        MessageRecord.family_id == current_user.family_id,
        MessageRecord.id.in_(message_ids),
    ).all()
    if not records:
        flash("No matching alerts were found.", "warning")
        return redirect(url_for("parent.alerts"))

    deleted_count = len(records)
    subject_ids = {record.submitted_by_id for record in records if record.submitted_by_id}
    for record in records:
        db.session.delete(record)
    log_event(
        current_user.family_id,
        current_user.id,
        "messages_bulk_deleted",
        f"Deleted {deleted_count} selected alert(s)",
        subject_user_id=next(iter(subject_ids), None),
    )
    db.session.commit()
    flash(f"{deleted_count} alert(s) deleted.", "success")
    return redirect(url_for("parent.alerts"))


@parent_bp.post("/logout-requests/<int:request_id>/approve")
def approve_logout(request_id: int):
    logout_request = LogoutRequest.query.filter_by(
        id=request_id, family_id=current_user.family_id, status="pending"
    ).first_or_404()
    _resolve_logout_request(logout_request, "approved")
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


@parent_bp.post("/logout-requests/<int:request_id>/deny")
def deny_logout(request_id: int):
    logout_request = LogoutRequest.query.filter_by(
        id=request_id, family_id=current_user.family_id, status="pending"
    ).first_or_404()
    _resolve_logout_request(logout_request, "denied")
    log_event(
        current_user.family_id,
        current_user.id,
        "logout_denied",
        f"Denied sign-out for child user {logout_request.child_user_id}. The child session stays active on this device.",
        subject_user_id=logout_request.child_user_id,
    )
    db.session.commit()
    flash("Logout denied. The child session remains active.", "info")
    return redirect(url_for("parent.alerts"))
