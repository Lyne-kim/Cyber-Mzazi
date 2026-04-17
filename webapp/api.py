from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from .extensions import db
from .models import (
    ActivityLog,
    Family,
    LogoutRequest,
    MessageRecord,
    NotificationIngestionDevice,
    SafetyResourceDocument,
    User,
)
from .services.audit import log_event
from .services.family_context import get_selected_child, set_selected_child
from .services.ml_service import get_classifier
from .services.notification_devices import (
    issue_ingestion_token,
    touch_ingestion_device,
    verify_ingestion_token,
)
from .services.verification import verify_message
from .ui_text import SUPPORTED_LANGUAGES, get_language


api_bp = Blueprint("api", __name__, url_prefix="/api")


def _error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "role": user.role,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "username": user.username,
        "family_id": user.family_id,
        "preferred_language": user.preferred_language,
    }


def _message_payload(message: MessageRecord) -> dict:
    return {
        "id": message.id,
        "source_platform": message.source_platform,
        "source_app_package": message.source_app_package,
        "sender_handle": message.sender_handle,
        "browser_origin": message.browser_origin,
        "notification_title": message.notification_title,
        "message_text": message.message_text,
        "capture_method": message.capture_method,
        "predicted_label": message.predicted_label,
        "predicted_confidence": message.predicted_confidence,
        "risk_indicators": message.risk_indicators,
        "verification_status": message.verification_status,
        "verification_label": message.verification_label,
        "verification_confidence": message.verification_confidence,
        "verification_notes": message.verification_notes,
        "reviewed_label": message.reviewed_label,
        "created_at": message.created_at.isoformat(),
    }


def _notification_device_payload(device: NotificationIngestionDevice) -> dict:
    return {
        "id": device.id,
        "child_user_id": device.child_user_id,
        "device_name": device.device_name,
        "platform": device.platform,
        "permission_scope": device.permission_scope,
        "status": device.status,
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        "last_ingested_at": device.last_ingested_at.isoformat() if device.last_ingested_at else None,
        "last_notification_app": device.last_notification_app,
        "created_at": device.created_at.isoformat(),
    }


def _log_payload(log: ActivityLog) -> dict:
    return {
        "id": log.id,
        "event_type": log.event_type,
        "details": log.details,
        "created_at": log.created_at.isoformat(),
        "actor_id": log.actor_id,
        "subject_user_id": log.subject_user_id,
    }


def _document_payload(document: SafetyResourceDocument) -> dict:
    return {
        "id": document.id,
        "filename": document.filename,
        "content_type": document.content_type,
        "file_size": document.file_size,
        "created_at": document.created_at.isoformat(),
        "uploaded_by_id": document.uploaded_by_id,
        "download_url": f"/parent/safety-resources/documents/{document.id}",
    }


def _logout_request_payload(item: LogoutRequest) -> dict:
    return {
        "id": item.id,
        "child_user_id": item.child_user_id,
        "status": item.status,
        "action_type": item.action_type,
        "action_description": item.action_description,
        "request_note": item.request_note,
        "created_at": item.created_at.isoformat(),
        "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
        "resolved_by_id": item.resolved_by_id,
        "resolved_by_name": item.resolved_by.name if item.resolved_by else None,
    }


def _parent_page_payload() -> dict:
    selected_child, children = get_selected_child(current_user.family_id)
    linked_devices = (
        NotificationIngestionDevice.query.filter_by(
            family_id=current_user.family_id,
            child_user_id=selected_child.id if selected_child else None,
        )
        .order_by(NotificationIngestionDevice.created_at.desc())
        .all()
    )
    if selected_child is None:
        messages = []
        logout_requests = []
        activity_logs = []
        approval_history = []
    else:
        messages = (
            MessageRecord.query.filter_by(
                family_id=current_user.family_id,
                submitted_by_id=selected_child.id,
            )
            .order_by(MessageRecord.created_at.desc())
            .limit(20)
            .all()
        )
        logout_requests = (
            LogoutRequest.query.filter_by(
                family_id=current_user.family_id,
                child_user_id=selected_child.id,
                status="pending",
            )
            .order_by(LogoutRequest.created_at.desc())
            .all()
        )
        activity_logs = (
            ActivityLog.query.filter(ActivityLog.family_id == current_user.family_id)
            .filter(
                or_(
                    ActivityLog.subject_user_id == selected_child.id,
                    ActivityLog.actor_id == selected_child.id,
                )
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(30)
            .all()
        )
        approval_history = (
            LogoutRequest.query.filter_by(
                family_id=current_user.family_id,
                child_user_id=selected_child.id,
            )
            .order_by(LogoutRequest.created_at.desc())
            .limit(20)
            .all()
        )
    documents = (
        SafetyResourceDocument.query.filter_by(family_id=current_user.family_id)
        .order_by(SafetyResourceDocument.created_at.desc())
        .all()
    )
    logout_request_cards = []
    for item in logout_requests:
        logout_request_cards.append(
            {
                **_logout_request_payload(item),
                "detail": item.action_description
                or "Child requested sign-out from this device.",
            }
        )
    high_risk_count = sum(1 for message in messages if message.predicted_label != "safe")
    reviewed_count = sum(1 for message in messages if message.reviewed_label)
    alert_count = high_risk_count + len(logout_requests)
    latest_sync = activity_logs[0].created_at.isoformat() if activity_logs else None
    return {
        "children": [_user_payload(child) for child in children],
        "selected_child": None if selected_child is None else _user_payload(selected_child),
        "messages": [_message_payload(message) for message in messages],
        "logout_requests": logout_request_cards,
        "selected_logout_request": logout_request_cards[0] if logout_request_cards else None,
        "activity_logs": [_log_payload(log) for log in activity_logs],
        "approval_history": [_logout_request_payload(item) for item in approval_history],
        "linked_devices": [_notification_device_payload(device) for device in linked_devices],
        "safety_documents": [_document_payload(document) for document in documents],
        "summary": {
            "alert_count": alert_count,
            "high_risk_count": high_risk_count,
            "reviewed_count": reviewed_count,
            "latest_sync": latest_sync,
            "child_display_name": selected_child.name if selected_child else None,
            "android_device_count": len(linked_devices),
        },
        "language": {"active": get_language(), "options": SUPPORTED_LANGUAGES},
    }


def _child_page_payload() -> dict:
    messages = (
        MessageRecord.query.filter_by(family_id=current_user.family_id)
        .order_by(MessageRecord.created_at.desc())
        .limit(15)
        .all()
    )
    pending_logout = (
        LogoutRequest.query.filter_by(
            family_id=current_user.family_id,
            child_user_id=current_user.id,
        )
        .filter(LogoutRequest.status.in_(["pending", "approved"]))
        .order_by(LogoutRequest.updated_at.desc())
        .first()
    )
    return {
        "messages": [_message_payload(message) for message in messages],
        "pending_logout": None if pending_logout is None else _logout_request_payload(pending_logout),
        "child_name": current_user.name,
        "language": {"active": get_language(), "options": SUPPORTED_LANGUAGES},
    }


@api_bp.get("/health")
def health():
    classifier = get_classifier()
    return jsonify(
        {
            "ok": True,
            "service": "cyber-mzazi-api",
            "model_loaded": classifier is not None,
        }
    )


@api_bp.post("/auth/register")
def register_family():
    payload = request.get_json(silent=True) or {}
    required_fields = [
        "family_name",
        "parent_name",
        "parent_contact",
        "parent_password",
        "child_name",
        "child_username",
        "child_password",
    ]
    missing = [field for field in required_fields if not str(payload.get(field, "")).strip()]
    if missing:
        return _error(f"Missing required fields: {', '.join(missing)}")

    parent_contact = str(payload["parent_contact"]).strip()
    child_username = str(payload["child_username"]).strip()
    if Family.query.filter_by(parent_contact=parent_contact).first():
        return _error("Parent contact already exists.", 409)
    if User.query.filter_by(username=child_username).first():
        return _error("Child username already exists.", 409)

    family = Family(
        family_name=str(payload["family_name"]).strip(),
        parent_contact=parent_contact,
        child_display_name=str(payload["child_name"]).strip(),
    )
    parent_user = User(
        family=family,
        role="parent",
        name=str(payload["parent_name"]).strip(),
        email=parent_contact if "@" in parent_contact else None,
        phone=parent_contact if "@" not in parent_contact else None,
        logout_requires_parent_approval=False,
        preferred_language="en",
    )
    parent_user.set_password(str(payload["parent_password"]))

    child_user = User(
        family=family,
        role="child",
        name=str(payload["child_name"]).strip(),
        username=child_username,
        logout_requires_parent_approval=True,
        preferred_language="en",
    )
    child_user.set_password(str(payload["child_password"]))

    db.session.add_all([family, parent_user, child_user])
    db.session.flush()
    log_event(
        family.id,
        parent_user.id,
        "family_registered",
        "Family account created via API",
        subject_user_id=child_user.id,
    )
    db.session.commit()

    return (
        jsonify(
            {
                "ok": True,
                "family": {
                    "id": family.id,
                    "family_name": family.family_name,
                    "parent_contact": family.parent_contact,
                    "child_display_name": family.child_display_name,
                },
                "parent": _user_payload(parent_user),
                "child": _user_payload(child_user),
            }
        ),
        201,
    )


@api_bp.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    portal = str(payload.get("portal", "parent")).strip().lower()
    password = str(payload.get("password", ""))

    if portal == "parent":
        identifier = str(payload.get("identifier", "")).strip()
        user = User.query.filter(
            User.role == "parent", or_(User.email == identifier, User.phone == identifier)
        ).first()
    elif portal == "child":
        parent_contact = str(payload.get("parent_contact", "")).strip()
        child_username = str(payload.get("child_username", "")).strip()
        user = (
            User.query.join(Family)
            .filter(
                User.role == "child",
                User.username == child_username,
                Family.parent_contact == parent_contact,
            )
            .first()
        )
    else:
        return _error("Portal must be either parent or child.")

    if not user or not user.check_password(password):
        return _error("Invalid login details.", 401)

    login_user(user)
    log_event(
        user.family_id,
        user.id,
        "login",
        f"{user.role} logged in via API",
        subject_user_id=user.id if user.role == "child" else None,
    )
    db.session.commit()
    return jsonify({"ok": True, "user": _user_payload(user)})


@api_bp.post("/auth/logout")
@login_required
def logout():
    if current_user.role == "child" and current_user.logout_requires_parent_approval:
        approval = (
            LogoutRequest.query.filter_by(
                family_id=current_user.family_id,
                child_user_id=current_user.id,
                status="approved",
            )
            .order_by(LogoutRequest.updated_at.desc())
            .first()
        )
        if not approval:
            return _error("Parent approval is required before this child session can sign out.", 403)
        approval.status = "used"
        db.session.add(approval)

    family_id = current_user.family_id
    actor_id = current_user.id
    role = current_user.role
    logout_user()
    log_event(
        family_id,
        actor_id,
        "logout",
        f"{role} logged out via API",
        subject_user_id=actor_id if role == "child" else None,
    )
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.get("/me")
@login_required
def current_session():
    return jsonify({"ok": True, "user": _user_payload(current_user)})


@api_bp.get("/parent/dashboard")
@login_required
def parent_dashboard():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify({"ok": True, "page": "dashboard", **_parent_page_payload()})


@api_bp.get("/parent/alerts")
@login_required
def parent_alerts():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify({"ok": True, "page": "alerts", **_parent_page_payload()})


@api_bp.get("/parent/child-profile")
@login_required
def parent_child_profile():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    selected_child, _children = get_selected_child(current_user.family_id)
    return jsonify(
        {
            "ok": True,
            "page": "child_profile",
            "child_profile": {
                "display_name": selected_child.name if selected_child else None,
                "safety_mode": "Safety Check",
                "linked_device": "Shared family session",
                "protected_sign_out": True,
                "scope": "Incoming third-party messages and links",
            },
            **_parent_page_payload(),
        }
    )


@api_bp.get("/parent/activity-log")
@login_required
def parent_activity_log():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify({"ok": True, "page": "activity_log", **_parent_page_payload()})


@api_bp.get("/parent/alert-settings")
@login_required
def parent_alert_settings():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify(
        {
            "ok": True,
            "page": "alert_settings",
            "settings": {
                "threat_threshold": "Medium + High",
                "notification_channels": ["in-app", "email"],
                "quiet_hours": "22:00 - 06:00",
                "pause_monitoring_enabled": False,
            },
            **_parent_page_payload(),
        }
    )


@api_bp.get("/parent/family-hub")
@login_required
def parent_family_hub():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify({"ok": True, "page": "family_hub", **_parent_page_payload()})


@api_bp.get("/parent/safety-resources")
@login_required
def parent_safety_resources():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify({"ok": True, "page": "safety_resources", **_parent_page_payload()})


@api_bp.get("/parent/help-support")
@login_required
def parent_help_support():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify({"ok": True, "page": "help_support", **_parent_page_payload()})


@api_bp.get("/parent/privacy-center")
@login_required
def parent_privacy_center():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify({"ok": True, "page": "privacy_center", **_parent_page_payload()})


@api_bp.get("/parent/system-status")
@login_required
def parent_system_status():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify({"ok": True, "page": "system_status", **_parent_page_payload()})


@api_bp.get("/parent/insights")
@login_required
def parent_insights():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify({"ok": True, "page": "insights", **_parent_page_payload()})


@api_bp.get("/parent/language-settings")
@login_required
def parent_language_settings():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify({"ok": True, "page": "language_settings", **_parent_page_payload()})


@api_bp.get("/parent/notification-log")
@login_required
def parent_notification_log():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify({"ok": True, "page": "notification_log", **_parent_page_payload()})


@api_bp.get("/parent/trusted-contacts")
@login_required
def parent_trusted_contacts():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    return jsonify({"ok": True, "page": "trusted_contacts", **_parent_page_payload()})


@api_bp.post("/parent/messages/<int:message_id>/review")
@login_required
def review_message(message_id: int):
    if current_user.role != "parent":
        return _error("Parent access only.", 403)

    payload = request.get_json(silent=True) or {}
    reviewed_label = str(payload.get("reviewed_label", "")).strip()
    if not reviewed_label:
        return _error("Reviewed label is required.")

    record = MessageRecord.query.filter_by(
        id=message_id, family_id=current_user.family_id
    ).first()
    if record is None:
        return _error("Message not found.", 404)

    record.reviewed_label = reviewed_label
    record.reviewed_by_id = current_user.id
    log_event(
        current_user.family_id,
        current_user.id,
        "message_reviewed",
        f"Message {record.id} reviewed as {reviewed_label} via API",
        subject_user_id=record.submitted_by_id,
    )
    db.session.commit()
    return jsonify({"ok": True, "message": _message_payload(record)})


@api_bp.post("/parent/logout-requests/<int:request_id>/approve")
@login_required
def approve_logout(request_id: int):
    if current_user.role != "parent":
        return _error("Parent access only.", 403)

    logout_request = LogoutRequest.query.filter_by(
        id=request_id, family_id=current_user.family_id, status="pending"
    ).first()
    if logout_request is None:
        return _error("Logout request not found.", 404)

    logout_request.status = "approved"
    logout_request.resolved_by_id = current_user.id
    logout_request.resolved_at = datetime.utcnow()
    log_event(
        current_user.family_id,
        current_user.id,
        "logout_approved",
        f"Approved sign-out for child user {logout_request.child_user_id} via API. The child device can close the current child session once.",
        subject_user_id=logout_request.child_user_id,
    )
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.post("/parent/select-child")
@login_required
def parent_select_child():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    payload = request.get_json(silent=True) or {}
    child = set_selected_child(current_user.family_id, int(payload.get("child_id", 0)))
    if child is None:
        return _error("Child profile not found.", 404)
    return jsonify({"ok": True, "selected_child": _user_payload(child)})


@api_bp.post("/parent/family-hub/children")
@login_required
def parent_add_child():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    payload = request.get_json(silent=True) or {}
    child_name = str(payload.get("child_name", "")).strip()
    child_username = str(payload.get("child_username", "")).strip()
    child_password = str(payload.get("child_password", ""))
    preferred_language = str(payload.get("preferred_language", "en")).strip().lower()
    if not all([child_name, child_username, child_password]):
        return _error("child_name, child_username, and child_password are required.")
    if preferred_language not in SUPPORTED_LANGUAGES:
        preferred_language = "en"
    if User.query.filter_by(username=child_username).first():
        return _error("Child username already exists.", 409)

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
        f"Added child profile {child_name} via API",
        subject_user_id=child_user.id,
    )
    db.session.commit()
    return jsonify({"ok": True, "child": _user_payload(child_user)}), 201


@api_bp.post("/parent/safety-resources/documents")
@login_required
def parent_upload_resource_documents():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    uploads = [upload for upload in request.files.getlist("attachments") if upload and upload.filename]
    if not uploads:
        return _error("Choose one or more documents first.")

    documents = []
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
        documents.append(document)
        saved_names.append(upload.filename)

    log_event(
        current_user.family_id,
        current_user.id,
        "resource_attachment_added",
        f"Uploaded safety resource documents via API: {', '.join(saved_names)}",
    )
    db.session.commit()
    return jsonify({"ok": True, "documents": [_document_payload(document) for document in documents]}), 201


@api_bp.post("/parent/android-devices")
@login_required
def parent_create_android_device():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    payload = request.get_json(silent=True) or {}
    selected_child, _children = get_selected_child(current_user.family_id)
    child_user_id = int(payload.get("child_user_id") or (selected_child.id if selected_child else 0))
    device_name = str(payload.get("device_name", "")).strip()
    if not child_user_id:
        return _error("Select a child profile before creating an Android link.")
    if not device_name:
        return _error("device_name is required.")

    child_user = User.query.filter_by(
        id=child_user_id,
        family_id=current_user.family_id,
        role="child",
    ).first()
    if child_user is None:
        return _error("Child profile not found.", 404)

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
        f"Created Android notification link '{device_name}' for {child_user.name} via API",
        subject_user_id=child_user.id,
    )
    db.session.commit()
    return (
        jsonify(
            {
                "ok": True,
                "device": _notification_device_payload(device),
                "ingest_token": ingest_token,
                "instructions": {
                    "header": "Authorization: Bearer <token> or X-Cyber-Mzazi-Device-Key",
                    "endpoint": "/api/device-ingest/android-notifications",
                    "scope": "notification_listener",
                    "pairing_uri": (
                        "cybermzazi://pair"
                        f"?base_url={quote(request.url_root.rstrip('/'), safe='')}"
                        f"&token={quote(ingest_token, safe='')}"
                        f"&device_name={quote(device_name, safe='')}"
                    ),
                },
            }
        ),
        201,
    )


@api_bp.post("/parent/android-devices/<int:device_id>/disable")
@login_required
def parent_disable_android_device(device_id: int):
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    device = NotificationIngestionDevice.query.filter_by(
        id=device_id,
        family_id=current_user.family_id,
    ).first()
    if device is None:
        return _error("Linked Android device not found.", 404)
    device.status = "disabled"
    log_event(
        current_user.family_id,
        current_user.id,
        "android_device_link_disabled",
        f"Disabled Android notification link '{device.device_name}' via API",
        subject_user_id=device.child_user_id,
    )
    db.session.commit()
    return jsonify({"ok": True, "device": _notification_device_payload(device)})


@api_bp.post("/device-ingest/android-notifications")
def ingest_android_notification():
    token = request.headers.get("X-Cyber-Mzazi-Device-Key", "").strip()
    auth_header = request.headers.get("Authorization", "").strip()
    if not token and auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    device = verify_ingestion_token(token)
    if device is None:
        return _error("Valid device ingestion token is required.", 401)

    classifier = get_classifier()
    if classifier is None:
        return _error("Model is not ready.", 503)

    payload = request.get_json(silent=True) or {}
    message_text = str(payload.get("message_text") or payload.get("notification_text", "")).strip()
    source_platform = str(payload.get("source_platform") or payload.get("app_name", "")).strip() or "social media"
    app_package = str(payload.get("app_package", "")).strip() or None
    sender_handle = str(payload.get("sender_handle", "")).strip() or None
    browser_origin = str(payload.get("browser_origin") or payload.get("deep_link", "")).strip() or None
    notification_title = str(payload.get("notification_title", "")).strip() or None

    if not message_text:
        return _error("message_text or notification_text is required.")

    prediction = classifier.predict(message_text)
    verification = verify_message(message_text, prediction["label"])

    record = MessageRecord(
        family_id=device.family_id,
        submitted_by_id=device.child_user_id,
        source_platform=source_platform,
        source_app_package=app_package,
        sender_handle=sender_handle,
        browser_origin=browser_origin,
        notification_title=notification_title,
        message_text=message_text,
        capture_method="android_notification",
        predicted_label=prediction["label"],
        predicted_confidence=prediction["confidence"],
        risk_indicators=prediction["risk_indicators"],
        verification_status=verification["status"],
        verification_label=verification["label"],
        verification_confidence=verification["confidence"],
        verification_notes=verification["notes"],
    )
    db.session.add(record)
    touch_ingestion_device(device, source_platform=source_platform)
    log_event(
        device.family_id,
        None,
        "android_notification_ingested",
        (
            f"Android notification ingested from {source_platform}"
            f"{f' ({device.device_name})' if device.device_name else ''}."
        ),
        subject_user_id=device.child_user_id,
    )
    db.session.commit()
    return jsonify({"ok": True, "message": _message_payload(record), "device": _notification_device_payload(device)}), 201


@api_bp.get("/child/dashboard")
@login_required
def child_dashboard():
    if current_user.role != "child":
        return _error("Child access only.", 403)
    return jsonify({"ok": True, "page": "home", **_child_page_payload()})


@api_bp.get("/child/home")
@login_required
def child_home():
    if current_user.role != "child":
        return _error("Child access only.", 403)
    return jsonify({"ok": True, "page": "home", **_child_page_payload()})


@api_bp.get("/child/report")
@login_required
def child_report():
    if current_user.role != "child":
        return _error("Child access only.", 403)
    return jsonify({"ok": True, "page": "report", **_child_page_payload()})


@api_bp.get("/child/my-safety")
@login_required
def child_my_safety():
    if current_user.role != "child":
        return _error("Child access only.", 403)
    return jsonify({"ok": True, "page": "my_safety", **_child_page_payload()})


@api_bp.get("/child/talk")
@login_required
def child_talk():
    if current_user.role != "child":
        return _error("Child access only.", 403)
    return jsonify({"ok": True, "page": "talk", **_child_page_payload()})


@api_bp.get("/child/help")
@login_required
def child_help():
    if current_user.role != "child":
        return _error("Child access only.", 403)
    return jsonify({"ok": True, "page": "help", **_child_page_payload()})


@api_bp.get("/child/settings")
@login_required
def child_settings():
    if current_user.role != "child":
        return _error("Child access only.", 403)
    return jsonify({"ok": True, "page": "settings", **_child_page_payload()})


@api_bp.post("/child/messages")
@login_required
def submit_message():
    if current_user.role != "child":
        return _error("Child access only.", 403)

    classifier = get_classifier()
    if classifier is None:
        return _error("Train the model first with `flask train-models`.", 503)

    payload = request.get_json(silent=True) or {}
    message_text = str(payload.get("message_text", "")).strip()
    source_platform = str(payload.get("source_platform", "social media")).strip() or "social media"
    sender_handle = str(payload.get("sender_handle", "")).strip() or None
    browser_origin = str(payload.get("browser_origin", "")).strip() or None

    if not message_text:
        return _error("Message text is required.")

    prediction = classifier.predict(message_text)
    verification = verify_message(message_text, prediction["label"])

    record = MessageRecord(
        family_id=current_user.family_id,
        submitted_by_id=current_user.id,
        source_platform=source_platform,
        sender_handle=sender_handle,
        browser_origin=browser_origin,
        message_text=message_text,
        predicted_label=prediction["label"],
        predicted_confidence=prediction["confidence"],
        risk_indicators=prediction["risk_indicators"],
        verification_status=verification["status"],
        verification_label=verification["label"],
        verification_confidence=verification["confidence"],
        verification_notes=verification["notes"],
    )
    db.session.add(record)
    log_event(
        current_user.family_id,
        current_user.id,
        "message_submitted",
        f"Flagged an incoming message from {source_platform} for safety analysis via API",
        subject_user_id=current_user.id,
    )
    db.session.commit()
    return jsonify({"ok": True, "message": _message_payload(record)}), 201


@api_bp.post("/child/logout-request")
@login_required
def request_logout():
    if current_user.role != "child":
        return _error("Child access only.", 403)

    existing = LogoutRequest.query.filter_by(
        family_id=current_user.family_id,
        child_user_id=current_user.id,
        status="pending",
    ).first()
    if existing:
        return _error("A logout request is already pending.", 409)

    payload = request.get_json(silent=True) or {}
    request_note = str(payload.get("request_note", "")).strip()
    request_details = (
        "Child requested sign-out from this device. "
        "This request ends only the current child session on this device."
    )
    if request_note:
        request_details = f"{request_details} Note from child device: {request_note}"

    logout_request = LogoutRequest(
        family_id=current_user.family_id,
        child_user_id=current_user.id,
        action_type="session_logout",
        action_description=(
            "Child requested sign-out from this device. "
            "This request ends only the current child session on this device."
        ),
        request_note=request_note or None,
        status="pending",
    )
    db.session.add(logout_request)
    log_event(
        current_user.family_id,
        current_user.id,
        "logout_requested",
        f"{request_details} Requested via API.",
        subject_user_id=current_user.id,
    )
    db.session.commit()
    return (
        jsonify(
            {
                "ok": True,
                "logout_request": {
                    "id": logout_request.id,
                    "status": logout_request.status,
                    "created_at": logout_request.created_at.isoformat(),
                },
            }
        ),
        201,
    )


@api_bp.post("/ui/language")
@login_required
def set_ui_language():
    payload = request.get_json(silent=True) or {}
    language = str(payload.get("language", "en")).strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        return _error("Choose English or Swahili.")

    session["ui_language"] = language
    current_user.preferred_language = language
    log_event(
        current_user.family_id,
        current_user.id,
        "language_changed",
        f"{current_user.role.title()} interface language set to {SUPPORTED_LANGUAGES[language]} via API",
        subject_user_id=current_user.id if current_user.role == "child" else None,
    )
    db.session.commit()
    return jsonify({"ok": True, "language": {"active": language, "options": SUPPORTED_LANGUAGES}})


@api_bp.get("/activity")
@login_required
def activity():
    logs = (
        ActivityLog.query.filter_by(family_id=current_user.family_id)
        .order_by(ActivityLog.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify({"ok": True, "activity_logs": [_log_payload(log) for log in logs]})
