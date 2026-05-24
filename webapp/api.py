from __future__ import annotations

import secrets
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, current_app, jsonify, request, session
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from ml.labels import SUPPORTED_LABELS, label_summary_rows, label_title, label_tone
from ml.safe_overrides import safe_override_policy_summary, split_config_list

from .extensions import db
from .models import (
    ActivityLog,
    Family,
    LogoutRequest,
    MessageRecord,
    NotificationIngestionDevice,
    TrustedContact,
    User,
)
from .services.audit import log_event
from .services.cooldowns import resend_wait_seconds
from .services.email_verification import (
    send_verification_email,
    verify_email_token,
)
from .services.mail_delivery import is_mail_delivery_configured, send_email
from .services.family_context import get_selected_child, set_selected_child
from .services.message_suppression import is_message_suppressed, suppress_message
from .services.notification_devices import (
    issue_ingestion_token,
    touch_ingestion_device,
    verify_ingestion_token,
)
from .services.notification_grouping import split_notification_messages
from .services.parent_alerts import (
    send_high_risk_message_alert,
    send_logout_request_alert,
)
from .services.phone_verification import (
    is_sms_configured,
    normalize_phone,
    send_phone_verification_code,
    verify_phone_code,
)
from .services.prediction_service import (
    PredictionUnavailable,
    predict_message,
    prediction_backend_status,
)
from .services.review_feedback import build_review_signature
from .services.safety_assistant import build_safety_assistant_response
from .services.verification import verify_message
from .ui_text import SUPPORTED_LANGUAGES, get_language


api_bp = Blueprint("api", __name__, url_prefix="/api")

PUBLIC_API_ENDPOINTS = {
    "api.health",
    "api.developer_status",
    "api.developer_safe_overrides",
    "api.register_family",
    "api.login",
    "api.logout",
    "api.resend_verification",
    "api.resend_phone_verification",
    "api.verify_phone",
    "api.verify_email",
    "api.ingest_android_notification",
}


@api_bp.before_request
def require_verified_family_session():
    if request.endpoint in PUBLIC_API_ENDPOINTS or not current_user.is_authenticated:
        return None
    if current_user.role == "parent" and not current_user.can_log_in:
        logout_user()
        return _error("Verify the parent account before continuing.", 403)
    if current_user.role == "child":
        parent_user = _family_parent_for(current_user)
        if parent_user is None or not parent_user.can_log_in:
            logout_user()
            return _error("Verify the parent/guardian account before continuing.", 403)
    return None


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
        "email_verified": user.email_verified,
        "requires_email_verification": user.requires_email_verification,
        "phone_verified": user.phone_verified,
        "requires_phone_verification": user.requires_phone_verification,
    }


def _family_parent_for(user: User) -> User | None:
    return User.query.filter_by(family_id=user.family_id, role="parent").first()


def _parent_contact_exists(parent_contact: str) -> bool:
    return bool(
        Family.query.filter_by(parent_contact=parent_contact).first()
        or User.query.filter(
            User.role == "parent",
            or_(User.email == parent_contact, User.phone == parent_contact),
        ).first()
    )


def _verification_error_for(parent_user: User | None) -> str:
    if parent_user is None:
        return "Parent/guardian verification is required before continuing."
    if parent_user.requires_email_verification and not parent_user.email_verified:
        return "Verify the parent email address before signing in. Request a new verification email if needed."
    if parent_user.requires_phone_verification and not parent_user.phone_verified:
        return "Verify the parent phone number before signing in. Request a phone code if needed."
    return "Verify the parent account before signing in."


def _generate_short_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _password_change_verified() -> bool:
    verified_at = session.get("password_change_verified_at")
    verified_user_id = session.get("password_change_user_id")
    if not verified_at or verified_user_id != current_user.id:
        return False
    try:
        timestamp = datetime.fromisoformat(verified_at)
    except ValueError:
        return False
    max_age = int(current_app.config.get("PASSWORD_CHANGE_CODE_MAX_AGE", 900))
    return datetime.utcnow() <= timestamp + timedelta(seconds=max_age)


def _resolve_logout_request(logout_request: LogoutRequest, status: str) -> None:
    logout_request.status = status
    logout_request.resolved_by_id = current_user.id
    logout_request.resolved_at = datetime.utcnow()
    db.session.add(logout_request)


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
        "predicted_label_title": label_title(message.predicted_label),
        "predicted_label_tone": label_tone(message.predicted_label),
        "predicted_confidence": message.predicted_confidence,
        "risk_indicators": message.risk_indicators,
        "verification_status": message.verification_status,
        "verification_label": message.verification_label,
        "verification_label_title": label_title(message.verification_label),
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


def _truncate(value: object, limit: int) -> str | None:
    cleaned = str(value or "").strip()
    if not cleaned:
        return None
    return cleaned[:limit]


def _trusted_contact_payload(contact: TrustedContact) -> dict:
    return {
        "id": contact.id,
        "name": contact.name,
        "relationship": contact.relationship,
        "contact": contact.contact,
        "alert_access": contact.alert_access,
        "response_role": contact.response_role,
        "notes": contact.notes,
        "active": contact.active,
        "created_at": contact.created_at.isoformat(),
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
    trusted_contacts = (
        TrustedContact.query.filter_by(family_id=current_user.family_id)
        .order_by(TrustedContact.created_at.desc())
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
    label_breakdown = label_summary_rows(
        [message.predicted_label for message in messages if message.predicted_label and message.predicted_label != "safe"]
    )
    latest_sync = activity_logs[0].created_at.isoformat() if activity_logs else None
    return {
        "family": {
            "id": current_user.family.id,
            "family_name": current_user.family.family_name,
            "parent_contact": current_user.family.parent_contact,
            "child_display_name": current_user.family.child_display_name,
        },
        "children": [_user_payload(child) for child in children],
        "selected_child": None if selected_child is None else _user_payload(selected_child),
        "messages": [_message_payload(message) for message in messages],
        "logout_requests": logout_request_cards,
        "selected_logout_request": logout_request_cards[0] if logout_request_cards else None,
        "activity_logs": [_log_payload(log) for log in activity_logs],
        "approval_history": [_logout_request_payload(item) for item in approval_history],
        "linked_devices": [_notification_device_payload(device) for device in linked_devices],
        "trusted_contacts": [_trusted_contact_payload(contact) for contact in trusted_contacts],
        "summary": {
            "alert_count": alert_count,
            "high_risk_count": high_risk_count,
            "reviewed_count": reviewed_count,
            "label_breakdown": label_breakdown,
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
        .filter(LogoutRequest.status.in_(["pending", "approved", "denied"]))
        .order_by(LogoutRequest.created_at.desc())
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
    backend = prediction_backend_status()
    return jsonify(
        {
            "ok": True,
            "service": "cyber-mzazi-api",
            "model_loaded": backend["model_loaded"],
            "model_provider": backend["provider"],
            "model_endpoint": backend["endpoint"],
        }
    )


def _developer_status_authorized() -> bool:
    expected_token = str(current_app.config.get("DEVELOPER_STATUS_TOKEN", "")).strip()
    supplied_token = (
        request.headers.get("X-Developer-Token", "").strip()
        or request.args.get("token", "").strip()
    )
    return bool(expected_token and secrets.compare_digest(supplied_token, expected_token))


def _path_status(config_key: str) -> dict:
    raw_path = str(current_app.config.get(config_key, "")).strip()
    exists = bool(raw_path and Path(raw_path).exists())
    return {"path": raw_path, "exists": exists}


def _load_model_metrics() -> dict:
    metrics_path = str(current_app.config.get("MODEL_METRICS_PATH", "")).strip()
    if not metrics_path:
        return {"path": "", "exists": False, "summary": {}}
    path = Path(metrics_path)
    if not path.exists():
        return {"path": metrics_path, "exists": False, "summary": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"path": metrics_path, "exists": True, "error": str(exc), "summary": {}}
    summary = {
        "model_name": payload.get("model_name"),
        "rows_used": payload.get("rows_used"),
        "epochs": payload.get("epochs"),
        "batch_size": payload.get("batch_size"),
        "max_length": payload.get("max_length"),
        "validation_accuracy": payload.get("validation_accuracy"),
        "validation_macro_f1": payload.get("validation_macro_f1"),
        "validation_loss": payload.get("validation_loss"),
        "dataset_path": payload.get("dataset_path"),
        "trained_at": payload.get("trained_at") or payload.get("updated_at"),
        "labels": payload.get("labels"),
        "class_distribution": payload.get("class_distribution"),
        "epoch_history": payload.get("epoch_history"),
    }
    return {"path": metrics_path, "exists": True, "summary": summary}


def _database_status() -> dict:
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        db.session.rollback()
        return {"configured": True, "reachable": False, "message": str(exc)}
    return {"configured": True, "reachable": True, "message": "Database connection is healthy."}


SAFE_OVERRIDE_INDICATORS = (
    "trusted_service_sender",
    "service_callback_message",
    "safe_educational_phrase",
)


def _safe_override_query():
    return MessageRecord.query.filter(
        MessageRecord.predicted_label == "safe",
        MessageRecord.risk_indicators.in_(SAFE_OVERRIDE_INDICATORS),
    )


def _safe_override_diagnostics() -> dict:
    try:
        total = _safe_override_query().count()
        by_reason = {
            reason: MessageRecord.query.filter_by(
                predicted_label="safe",
                risk_indicators=reason,
            ).count()
            for reason in SAFE_OVERRIDE_INDICATORS
        }
        recent = (
            _safe_override_query()
            .order_by(MessageRecord.created_at.desc())
            .limit(12)
            .all()
        )
    except SQLAlchemyError as exc:
        db.session.rollback()
        return {
            "total": 0,
            "by_reason": {},
            "policy": safe_override_policy_summary(
                extra_prefixes=split_config_list(current_app.config.get("SAFE_MESSAGE_PREFIXES", "")),
                extra_source_patterns=split_config_list(current_app.config.get("SAFE_SENDER_PATTERNS", "")),
            ),
            "recent": [],
            "error": str(exc),
        }
    return {
        "total": total,
        "by_reason": by_reason,
        "policy": safe_override_policy_summary(
            extra_prefixes=split_config_list(current_app.config.get("SAFE_MESSAGE_PREFIXES", "")),
            extra_source_patterns=split_config_list(current_app.config.get("SAFE_SENDER_PATTERNS", "")),
        ),
        "recent": [_message_payload(message) for message in recent],
    }


def _recent_failure_diagnostics() -> list[dict]:
    failure_terms = (
        "%failed%",
        "%error%",
        "%could not%",
        "%timed out%",
        "%timeout%",
        "%denied%",
    )
    try:
        query = ActivityLog.query.filter(
            or_(
                ActivityLog.event_type.ilike("%failed%"),
                ActivityLog.event_type.ilike("%error%"),
                *[ActivityLog.details.ilike(term) for term in failure_terms],
            )
        )
        logs = query.order_by(ActivityLog.created_at.desc()).limit(20).all()
    except SQLAlchemyError:
        db.session.rollback()
        return []
    return [
        {
            "id": item.id,
            "family_id": item.family_id,
            "event_type": item.event_type,
            "details": item.details,
            "actor_id": item.actor_id,
            "subject_user_id": item.subject_user_id,
            "created_at": item.created_at.isoformat(),
        }
        for item in logs
    ]


@api_bp.get("/developer/status")
def developer_status():
    if not _developer_status_authorized():
        return _error("Not found.", 404)
    backend = prediction_backend_status()
    metrics = _load_model_metrics()
    artifact_labels = metrics.get("summary", {}).get("labels") or []
    return jsonify(
        {
            "ok": True,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "dataset": _path_status("DATASET_PATH"),
            "model_artifact": _path_status("MODEL_ARTIFACT_PATH"),
            "model_metrics": metrics,
            "labels": {
                "code": SUPPORTED_LABELS,
                "artifact": artifact_labels,
                "match": not artifact_labels or list(artifact_labels) == SUPPORTED_LABELS,
            },
            "model": {
                "provider_config": current_app.config.get("MODEL_PROVIDER"),
                "runtime_provider": backend["provider"],
                "loaded": backend["model_loaded"],
                "endpoint_configured": bool(current_app.config.get("MODEL_API_URL")),
                "endpoint": backend["endpoint"],
                "heuristic_fallback": bool(current_app.config.get("ENABLE_HEURISTIC_FALLBACK")),
                "review_feedback_matching": bool(current_app.config.get("ENABLE_REVIEW_FEEDBACK_MATCHING")),
            },
            "configuration": {
                "database": _database_status(),
                "mail": {
                    "configured": is_mail_delivery_configured(),
                    "server": current_app.config.get("MAIL_SERVER"),
                    "port": current_app.config.get("MAIL_PORT"),
                    "sender_configured": bool(
                        current_app.config.get("MAIL_DEFAULT_SENDER")
                        or current_app.config.get("MAIL_USERNAME")
                    ),
                },
                "sms": {
                    "provider": current_app.config.get("SMS_PROVIDER"),
                    "configured": is_sms_configured(),
                    "shortcode_configured": bool(current_app.config.get("TEXTSMS_SHORTCODE")),
                    "partner_configured": bool(current_app.config.get("TEXTSMS_PARTNER_ID")),
                    "endpoint_configured": bool(current_app.config.get("TEXTSMS_ENDPOINT")),
                },
                "app_base_url_configured": bool(current_app.config.get("APP_BASE_URL")),
            },
            "safe_overrides": _safe_override_diagnostics(),
            "recent_failures": _recent_failure_diagnostics(),
        }
    )


@api_bp.get("/developer/safe-overrides")
def developer_safe_overrides():
    if not _developer_status_authorized():
        return _error("Not found.", 404)
    return jsonify({"ok": True, **_safe_override_diagnostics()})


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
    parent_contact = parent_contact if "@" in parent_contact else normalize_phone(parent_contact)
    child_username = str(payload["child_username"]).strip()
    if _parent_contact_exists(parent_contact):
        return _error("Parent contact already exists.", 409)

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
        phone=normalize_phone(parent_contact) if "@" not in parent_contact else None,
        logout_requires_parent_approval=False,
        preferred_language="en",
        email_verified=False,
        phone_verified=False,
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
    try:
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return _error("Parent email or phone is already in use.", 409)
    log_event(
        family.id,
        parent_user.id,
        "family_registered",
        "Family account created via API",
        subject_user_id=child_user.id,
    )
    verification_sent = False
    verification_message = None
    phone_verification_sent = False
    phone_verification_message = None
    if parent_user.requires_email_verification:
        try:
            verification_sent, verification_message = send_verification_email(parent_user)
        except Exception as exc:  # pragma: no cover - external mail provider dependent
            verification_sent = False
            verification_message = f"Verification email could not be sent: {exc}"
        if verification_sent:
            log_event(
                family.id,
                parent_user.id,
                "verification_email_sent",
                f"Verification email sent to {parent_user.email} via API",
            )
    if parent_user.requires_phone_verification:
        try:
            phone_verification_sent, phone_verification_message = send_phone_verification_code(parent_user)
        except Exception as exc:  # pragma: no cover - external SMS provider dependent
            phone_verification_sent = False
            phone_verification_message = f"Phone verification code could not be sent: {exc}"
        if phone_verification_sent:
            log_event(
                family.id,
                parent_user.id,
                "phone_verification_sent",
                f"Phone verification code sent to {parent_user.phone} via API",
            )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error("Parent email or phone is already in use.", 409)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("API family registration failed during database commit.")
        return _error("Family account could not be saved right now. Please try again.", 500)

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
                "requires_email_verification": parent_user.requires_email_verification,
                "requires_phone_verification": parent_user.requires_phone_verification,
                "email_verification_sent": verification_sent,
                "email_delivery_message": verification_message,
                "phone_verification_sent": phone_verification_sent,
                "phone_delivery_message": phone_verification_message,
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
        normalized_identifier = identifier if "@" in identifier else normalize_phone(identifier)
        user = User.query.filter(
            User.role == "parent",
            or_(User.email == identifier, User.phone == identifier, User.phone == normalized_identifier),
        ).first()
    elif portal == "child":
        raw_parent_contact = str(payload.get("parent_contact", "")).strip()
        parent_contact = raw_parent_contact if "@" in raw_parent_contact else normalize_phone(raw_parent_contact)
        child_username = str(payload.get("child_username", "")).strip()
        user = (
            User.query.join(Family)
            .filter(
                User.role == "child",
                User.username == child_username,
                or_(Family.parent_contact == raw_parent_contact, Family.parent_contact == parent_contact),
            )
            .first()
        )
    else:
        return _error("Portal must be either parent or child.")

    if not user or not user.check_password(password):
        return _error("Invalid login details.", 401)
    if portal == "parent" and not user.can_log_in:
        return _error(_verification_error_for(user), 403)
    if portal == "child":
        parent_user = _family_parent_for(user)
        if parent_user is None or not parent_user.can_log_in:
            return _error(_verification_error_for(parent_user), 403)

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


@api_bp.post("/auth/resend-verification")
def resend_verification():
    payload = request.get_json(silent=True) or {}
    identifier = str(payload.get("identifier", "")).strip()
    if not identifier:
        return _error("Parent email is required.")

    user = User.query.filter(
        User.role == "parent", or_(User.email == identifier, User.phone == identifier)
    ).first()
    if user is None or not user.email:
        return _error("Parent email account was not found.", 404)
    if user.email_verified:
        return _error("That email is already verified.", 409)
    wait_seconds = resend_wait_seconds(
        user.verification_email_sent_at,
        int(current_app.config.get("VERIFICATION_RESEND_COOLDOWN_SECONDS", 60)),
    )
    if wait_seconds:
        return _error(f"Wait {wait_seconds} seconds before requesting another email code.", 429)

    ok, message = send_verification_email(user)
    if not ok:
        db.session.rollback()
        return _error(message, 500)

    log_event(
        user.family_id,
        user.id,
        "verification_email_resent",
        f"Verification email resent to {user.email} via API",
    )
    db.session.commit()
    return jsonify({"ok": True, "message": message})


@api_bp.post("/auth/resend-phone-verification")
def resend_phone_verification():
    payload = request.get_json(silent=True) or {}
    identifier = str(payload.get("identifier", "")).strip()
    if not identifier:
        return _error("Parent phone number is required.")

    user = User.query.filter(
        User.role == "parent",
        or_(User.phone == identifier, User.phone == normalize_phone(identifier)),
    ).first()
    if user is None or not user.phone:
        return _error("Parent phone account was not found.", 404)
    if user.phone_verified:
        return _error("That phone number is already verified.", 409)
    wait_seconds = resend_wait_seconds(
        user.phone_verification_sent_at,
        int(current_app.config.get("VERIFICATION_RESEND_COOLDOWN_SECONDS", 60)),
    )
    if wait_seconds:
        return _error(f"Wait {wait_seconds} seconds before requesting another SMS code.", 429)

    ok, message = send_phone_verification_code(user)
    if not ok:
        db.session.rollback()
        return _error(message, 500)

    log_event(
        user.family_id,
        user.id,
        "phone_verification_resent",
        f"Phone verification code resent to {user.phone} via API",
    )
    db.session.commit()
    return jsonify({"ok": True, "message": message})


@api_bp.post("/auth/verify-phone")
def verify_phone():
    payload = request.get_json(silent=True) or {}
    identifier = str(payload.get("identifier", "")).strip()
    code = str(payload.get("code", "")).strip()
    if not identifier or not code:
        return _error("Parent phone number and verification code are required.")

    user = User.query.filter(
        User.role == "parent",
        or_(User.phone == identifier, User.phone == normalize_phone(identifier)),
    ).first()
    if user is None or not user.phone:
        return _error("Parent phone account was not found.", 404)

    ok, message = verify_phone_code(user, code)
    if not ok:
        db.session.rollback()
        return _error(message, 400)

    log_event(
        user.family_id,
        user.id,
        "phone_verified",
        f"Parent phone {user.phone} verified via API",
    )
    db.session.commit()
    return jsonify({"ok": True, "message": message, "user": _user_payload(user)})


@api_bp.post("/auth/verify-email")
def verify_email():
    payload = request.get_json(silent=True) or {}
    token = str(payload.get("token", "")).strip()
    if not token:
        return _error("Verification token is required.")

    user, error = verify_email_token(token)
    if error:
        return _error(error, 400)
    if user.email_verified:
        return jsonify({"ok": True, "message": "Email already verified.", "user": _user_payload(user)})

    user.email_verified = True
    user.email_verified_at = datetime.utcnow()
    db.session.add(user)
    log_event(
        user.family_id,
        user.id,
        "email_verified",
        f"Parent email {user.email} verified via API",
    )
    db.session.commit()
    return jsonify({"ok": True, "message": "Email verified successfully.", "user": _user_payload(user)})


@api_bp.get("/me")
@login_required
def current_session():
    return jsonify({"ok": True, "user": _user_payload(current_user)})


@api_bp.post("/assistant/chat")
@login_required
def assistant_chat():
    payload = request.get_json(silent=True) or {}
    prompt = str(payload.get("prompt", "")).strip()
    audience = current_user.role if current_user.role in {"parent", "child"} else "parent"
    result = build_safety_assistant_response(
        prompt,
        audience=audience,
        family_id=current_user.family_id,
    )
    if not result.get("ok"):
        return _error(result.get("error", "Assistant could not analyse that yet."), 400)
    guardian_alerted = False
    if (
        current_user.role == "child"
        and result.get("should_alert_guardian")
        and not is_message_suppressed(
            family_id=current_user.family_id,
            child_user_id=current_user.id,
            message_text=prompt,
        )
    ):
        record = MessageRecord(
            family_id=current_user.family_id,
            submitted_by_id=current_user.id,
            source_platform="AI Safety Assistant",
            sender_handle="Child question",
            message_text=prompt,
            review_signature=build_review_signature(prompt),
            capture_method="assistant_chat",
            predicted_label=result["label"],
            predicted_confidence=result["confidence"],
            risk_indicators=result["indicators"],
            verification_status="assistant_review",
            verification_label=result["label"],
            verification_confidence=result["confidence"],
            verification_notes=result["guidance"],
        )
        db.session.add(record)
        parent_user = current_user.family.users.filter_by(role="parent").first()
        email_alert_sent, _email_alert_message = send_high_risk_message_alert(parent_user, current_user, record)
        log_event(
            current_user.family_id,
            current_user.id,
            "assistant_high_risk_alert",
            "Child AI assistant API conversation created a parent dashboard alert.",
            subject_user_id=current_user.id,
        )
        if email_alert_sent and parent_user:
            log_event(
                current_user.family_id,
                parent_user.id,
                "parent_alert_emailed",
                f"Parent alert email sent for assistant message {record.id}.",
                subject_user_id=current_user.id,
            )
        db.session.commit()
        guardian_alerted = True
    return jsonify({"ok": True, "assistant": result, "guardian_alerted": guardian_alerted})


@api_bp.post("/account/profile")
@login_required
def update_profile():
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    contact = str(payload.get("contact", "")).strip()
    if not name:
        return _error("Name is required.")

    current_user.name = name
    if current_user.role == "parent" and contact:
        normalized_contact = contact if "@" in contact else normalize_phone(contact)
        old_email = current_user.email
        old_phone = current_user.phone
        existing = User.query.filter(
            User.id != current_user.id,
            User.role == "parent",
            or_(User.email == normalized_contact, User.phone == normalized_contact),
        ).first()
        existing_family = Family.query.filter(
            Family.id != current_user.family_id,
            Family.parent_contact == normalized_contact,
        ).first()
        if existing or existing_family:
            return _error("That parent contact is already in use.", 409)
        current_user.email = normalized_contact if "@" in normalized_contact else None
        current_user.phone = normalize_phone(normalized_contact) if "@" not in normalized_contact else None
        current_user.family.parent_contact = normalized_contact
        if current_user.email and current_user.email != old_email:
            current_user.email_verified = False
        if current_user.phone and current_user.phone != old_phone:
            current_user.phone_verified = False
    elif current_user.role == "child":
        # Child profiles can update their display name only. Parent contact and
        # child username stay owned by the parent/family account setup.
        pass

    log_event(
        current_user.family_id,
        current_user.id,
        "profile_updated",
        f"{current_user.role.title()} profile updated via API",
        subject_user_id=current_user.id if current_user.role == "child" else None,
    )
    db.session.commit()
    return jsonify({"ok": True, "user": _user_payload(current_user)})


@api_bp.post("/account/password-verification/send")
@login_required
def send_password_change_verification():
    payload = request.get_json(silent=True) or {}
    channel = str(payload.get("channel", "")).strip().lower()
    if not current_user.can_log_in:
        return _error("Verify email or phone before changing password.", 403)
    verification_user = _family_parent_for(current_user) if current_user.role == "child" else current_user
    if verification_user is None or not verification_user.can_log_in:
        return _error("Parent verification is required before changing password.", 403)
    if channel not in {"email", "phone"}:
        channel = "email" if verification_user.email else "phone"
    if channel == "phone":
        wait_seconds = resend_wait_seconds(
            verification_user.phone_verification_sent_at,
            int(current_app.config.get("VERIFICATION_RESEND_COOLDOWN_SECONDS", 60)),
        )
        if wait_seconds:
            return _error(f"Wait {wait_seconds} seconds before requesting another SMS code.", 429)
    else:
        try:
            sent_at = datetime.fromisoformat(str(session.get("password_change_code_sent_at", "")))
        except ValueError:
            sent_at = None
        wait_seconds = resend_wait_seconds(
            sent_at,
            int(current_app.config.get("VERIFICATION_RESEND_COOLDOWN_SECONDS", 60)),
        )
        if wait_seconds:
            return _error(f"Wait {wait_seconds} seconds before requesting another email code.", 429)

    code = _generate_short_code()
    max_age = int(current_app.config.get("PASSWORD_CHANGE_CODE_MAX_AGE", 900))
    max_age_minutes = max(1, max_age // 60)
    if channel == "email":
        if not verification_user.email:
            return _error("This account does not have an email address.")
        ok, message = send_email(
            verification_user.email,
            "Cyber Mzazi password change code",
            (
                f"Hello {current_user.name},\n\n"
                f"Your Cyber Mzazi password change code is {code}.\n"
                f"It expires in {max_age_minutes} minutes.\n\n"
                "If you did not request this, keep your current password and ignore this email."
            ),
        )
        if not ok:
            return _error(f"Password verification email could not be sent. {message}", 500)
        session["password_change_code_hash"] = generate_password_hash(code)
        session["password_change_code_channel"] = "email"
        session["password_change_code_sent_at"] = datetime.utcnow().isoformat()
        session["password_change_user_id"] = current_user.id
        return jsonify({"ok": True, "message": "Password verification code sent to email."})

    if not verification_user.phone:
        return _error("This account does not have a phone number.")
    ok, message = send_phone_verification_code(verification_user)
    if not ok:
        db.session.rollback()
        return _error(message, 500)
    session["password_change_code_channel"] = "phone"
    session["password_change_code_sent_at"] = datetime.utcnow().isoformat()
    session["password_change_user_id"] = current_user.id
    db.session.commit()
    return jsonify({"ok": True, "message": message})


@api_bp.post("/account/password-verification/confirm")
@login_required
def confirm_password_change_verification():
    payload = request.get_json(silent=True) or {}
    code = str(payload.get("code", "")).strip()
    channel = str(session.get("password_change_code_channel", "")).strip()
    if not code:
        return _error("Enter the password verification code.")
    if session.get("password_change_user_id") != current_user.id:
        return _error("Request a new password verification code.", 403)

    max_age = int(current_app.config.get("PASSWORD_CHANGE_CODE_MAX_AGE", 900))
    try:
        sent_at = datetime.fromisoformat(str(session.get("password_change_code_sent_at", "")))
    except ValueError:
        return _error("Request a new password verification code.", 403)
    if datetime.utcnow() > sent_at + timedelta(seconds=max_age):
        return _error("Password verification code expired. Request a new code.", 403)

    if channel == "email":
        code_hash = session.get("password_change_code_hash")
        if not code_hash or not check_password_hash(code_hash, code):
            return _error("Invalid password verification code.", 403)
    elif channel == "phone":
        verification_user = _family_parent_for(current_user) if current_user.role == "child" else current_user
        if verification_user is None:
            return _error("Request a new password verification code.", 403)
        if not verification_user.phone_verification_code_hash or not check_password_hash(
            verification_user.phone_verification_code_hash,
            code,
        ):
            return _error("Invalid password verification code.", 403)
        verification_user.phone_verification_code_hash = None
        db.session.add(verification_user)
    else:
        return _error("Request a new password verification code.", 403)

    session.pop("password_change_code_hash", None)
    session.pop("password_change_code_channel", None)
    session.pop("password_change_code_sent_at", None)
    session["password_change_verified_at"] = datetime.utcnow().isoformat()
    session["password_change_user_id"] = current_user.id
    log_event(
        current_user.family_id,
        current_user.id,
        "password_change_verified",
        f"{current_user.role.title()} confirmed password change verification via {channel}",
        subject_user_id=current_user.id if current_user.role == "child" else None,
    )
    db.session.commit()
    return jsonify({"ok": True, "message": "Password change verified."})


@api_bp.post("/account/change-password")
@login_required
def change_password():
    payload = request.get_json(silent=True) or {}
    current_password = str(payload.get("current_password", ""))
    new_password = str(payload.get("new_password", ""))
    if not current_password or not new_password:
        return _error("Current password and new password are required.")
    if len(new_password) < 8:
        return _error("New password must be at least 8 characters.")
    if not current_user.check_password(current_password):
        return _error("Current password is incorrect.", 403)
    if not current_user.can_log_in:
        return _error("Verify email or phone before changing password.", 403)
    if not _password_change_verified():
        return _error("Confirm the password verification code before changing password.", 403)

    current_user.set_password(new_password)
    session.pop("password_change_verified_at", None)
    session.pop("password_change_user_id", None)
    log_event(
        current_user.family_id,
        current_user.id,
        "password_changed",
        f"{current_user.role.title()} password changed via API",
        subject_user_id=current_user.id if current_user.role == "child" else None,
    )
    db.session.commit()
    return jsonify({"ok": True, "message": "Password changed."})


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


@api_bp.post("/parent/trusted-contacts")
@login_required
def parent_save_trusted_contact():
    if current_user.role != "parent":
        return _error("Parent access only.", 403)
    payload = request.get_json(silent=True) or {}
    contact_id = payload.get("id")
    name = str(payload.get("name", "")).strip()
    relationship = str(payload.get("relationship", "")).strip() or "Guardian"
    contact_value = str(payload.get("contact", "")).strip()
    alert_access = str(payload.get("alert_access", "critical")).strip().lower()
    response_role = str(payload.get("response_role", "backup")).strip().lower()
    notes = str(payload.get("notes", "")).strip()
    active = bool(payload.get("active", True))
    if alert_access not in {"none", "critical", "all"}:
        return _error("Alert access must be none, critical, or all.")
    if response_role not in {"viewer", "backup", "responder"}:
        return _error("Response role must be viewer, backup, or responder.")
    if not name or not contact_value:
        return _error("Guardian name and contact are required.")
    if contact_id:
        contact_item = TrustedContact.query.filter_by(
            id=int(contact_id),
            family_id=current_user.family_id,
        ).first()
        if contact_item is None:
            return _error("Trusted contact not found.", 404)
    else:
        contact_item = TrustedContact(
            family_id=current_user.family_id,
            created_by_id=current_user.id,
        )
        db.session.add(contact_item)
    contact_item.name = name
    contact_item.relationship = relationship
    contact_item.contact = contact_value
    contact_item.alert_access = alert_access
    contact_item.response_role = response_role
    contact_item.notes = notes or None
    contact_item.active = active
    log_event(
        current_user.family_id,
        current_user.id,
        "trusted_contact_saved",
        f"Trusted contact saved via API: {name} ({alert_access}, {response_role})",
    )
    db.session.commit()
    return jsonify({"ok": True, "trusted_contact": _trusted_contact_payload(contact_item)})


@api_bp.post("/parent/messages/<int:message_id>/review")
@login_required
def review_message(message_id: int):
    if current_user.role != "parent":
        return _error("Parent access only.", 403)

    payload = request.get_json(silent=True) or {}
    reviewed_label = str(payload.get("reviewed_label", "")).strip()
    if not reviewed_label:
        return _error("Reviewed label is required.")
    if reviewed_label not in SUPPORTED_LABELS:
        return _error("Reviewed label is invalid.")

    record = MessageRecord.query.filter_by(
        id=message_id, family_id=current_user.family_id
    ).first()
    if record is None:
        return _error("Message not found.", 404)

    record.reviewed_label = reviewed_label
    record.reviewed_by_id = current_user.id
    record.review_signature = build_review_signature(record.message_text)
    log_event(
        current_user.family_id,
        current_user.id,
        "message_reviewed",
        f"Message {record.id} reviewed as {reviewed_label} via API",
        subject_user_id=record.submitted_by_id,
    )
    db.session.commit()
    return jsonify({"ok": True, "message": _message_payload(record)})


@api_bp.post("/parent/messages/<int:message_id>/delete")
@login_required
def delete_message(message_id: int):
    if current_user.role != "parent":
        return _error("Parent access only.", 403)

    record = MessageRecord.query.filter_by(
        id=message_id,
        family_id=current_user.family_id,
    ).first()
    if record is None:
        return _error("Message not found.", 404)

    subject_user_id = record.submitted_by_id
    suppress_message(record, current_user.id)
    db.session.delete(record)
    log_event(
        current_user.family_id,
        current_user.id,
        "message_deleted",
        f"Deleted alert/message {message_id} via API",
        subject_user_id=subject_user_id,
    )
    db.session.commit()
    return jsonify({"ok": True})


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

    _resolve_logout_request(logout_request, "approved")
    log_event(
        current_user.family_id,
        current_user.id,
        "logout_approved",
        f"Approved sign-out for child user {logout_request.child_user_id} via API. The child device can close the current child session once.",
        subject_user_id=logout_request.child_user_id,
    )
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.post("/parent/logout-requests/<int:request_id>/deny")
@login_required
def deny_logout(request_id: int):
    if current_user.role != "parent":
        return _error("Parent access only.", 403)

    logout_request = LogoutRequest.query.filter_by(
        id=request_id, family_id=current_user.family_id, status="pending"
    ).first()
    if logout_request is None:
        return _error("Logout request not found.", 404)

    _resolve_logout_request(logout_request, "denied")
    log_event(
        current_user.family_id,
        current_user.id,
        "logout_denied",
        f"Denied sign-out for child user {logout_request.child_user_id} via API. The child session stays active on this device.",
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
    if User.query.filter_by(
        family_id=current_user.family_id,
        role="child",
        username=child_username,
    ).first():
        return _error("Child username already exists in this family.", 409)

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
                        "&role=child"
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

    payload = request.get_json(silent=True) or {}
    message_text = str(payload.get("message_text") or payload.get("notification_text", "")).strip()
    source_platform = _truncate(
        str(payload.get("source_platform") or payload.get("app_name", "")).strip()
        or "social media",
        60,
    )
    app_package = _truncate(payload.get("app_package"), 255)
    sender_handle = _truncate(payload.get("sender_handle"), 120)
    browser_origin = _truncate(payload.get("browser_origin") or payload.get("deep_link"), 255)
    notification_title = _truncate(payload.get("notification_title"), 255)

    if not message_text:
        return _error("message_text or notification_text is required.")

    notification_messages = split_notification_messages(
        message_text,
        sender_handle=sender_handle,
        notification_title=notification_title,
    )
    if not notification_messages:
        touch_ingestion_device(device, source_platform=source_platform)
        db.session.commit()
        return (
            jsonify(
                {
                    "ok": True,
                    "message": "Grouped notification summary ignored because it did not contain individual message text.",
                    "messages": [],
                    "ingested_count": 0,
                    "device": _notification_device_payload(device),
                    "parent_alert_email_sent": False,
                }
            ),
            202,
        )

    records: list[MessageRecord] = []
    skipped_suppressed = 0
    try:
        for notification_message in notification_messages:
            if is_message_suppressed(
                family_id=device.family_id,
                child_user_id=device.child_user_id,
                message_text=notification_message.text,
            ):
                skipped_suppressed += 1
                continue
            prediction = predict_message(
                notification_message.text,
                family_id=device.family_id,
                source_platform=source_platform,
                sender_handle=notification_message.sender_handle,
                app_package=app_package,
                notification_title=notification_message.notification_title,
            )
            try:
                verification = verify_message(notification_message.text, prediction.label)
            except Exception as exc:  # pragma: no cover - optional verifier failures are environment-dependent
                current_app.logger.exception("Message verification failed during Android ingestion.")
                verification = {
                    "status": "error",
                    "label": prediction.label,
                    "confidence": 0.0,
                    "notes": f"Verification failed: {exc}",
                }
            record = MessageRecord(
                family_id=device.family_id,
                submitted_by_id=device.child_user_id,
                source_platform=source_platform or "social media",
                source_app_package=app_package,
                sender_handle=_truncate(notification_message.sender_handle, 120),
                browser_origin=browser_origin,
                notification_title=_truncate(notification_message.notification_title, 255),
                message_text=notification_message.text,
                review_signature=build_review_signature(notification_message.text),
                capture_method="android_notification",
                predicted_label=prediction.label,
                predicted_confidence=prediction.confidence,
                risk_indicators=prediction.risk_indicators,
                verification_status=verification["status"],
                verification_label=verification["label"],
                verification_confidence=verification["confidence"],
                verification_notes=verification["notes"],
            )
            db.session.add(record)
            records.append(record)
    except PredictionUnavailable as exc:
        db.session.rollback()
        return _error(str(exc), 503)

    touch_ingestion_device(device, source_platform=source_platform)
    if not records:
        log_event(
            device.family_id,
            None,
            "android_notification_suppressed",
            (
                f"Android notification upload skipped {skipped_suppressed} deleted "
                f"message(s) from {source_platform}."
            ),
            subject_user_id=device.child_user_id,
        )
        db.session.commit()
        return (
            jsonify(
                {
                    "ok": True,
                    "message": "Previously deleted message(s) were ignored.",
                    "messages": [],
                    "ingested_count": 0,
                    "skipped_suppressed_count": skipped_suppressed,
                    "device": _notification_device_payload(device),
                    "parent_alert_email_sent": False,
                    "parent_alerts": [],
                }
            ),
            202,
        )
    log_event(
        device.family_id,
        None,
        "android_notification_ingested",
        (
            f"Android notification ingested {len(records)} message(s) from {source_platform}"
            f"{f' ({device.device_name})' if device.device_name else ''}."
        ),
        subject_user_id=device.child_user_id,
    )
    try:
        db.session.flush()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Android notification ingestion failed during database flush.")
        return _error("Notification upload could not be saved right now.", 500)

    parent_user = User.query.filter_by(family_id=device.family_id, role="parent").first()
    child_user = User.query.filter_by(id=device.child_user_id, role="child").first()
    parent_alerts = []
    for record in records:
        try:
            email_alert_sent, email_alert_message = send_high_risk_message_alert(parent_user, child_user, record)
        except Exception as exc:  # pragma: no cover - external mail provider dependent
            current_app.logger.exception("Parent alert email failed during Android ingestion.")
            email_alert_sent = False
            email_alert_message = f"Parent alert email failed: {exc}"
        if email_alert_sent and parent_user:
            log_event(
                device.family_id,
                parent_user.id,
                "parent_alert_emailed",
                f"Parent alert email sent for message {record.id}.",
                subject_user_id=device.child_user_id,
            )
        parent_alerts.append(
            {
                "message_id": record.id,
                "email_sent": email_alert_sent,
                "email_message": email_alert_message,
            }
        )
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Android notification ingestion failed during database commit.")
        return _error("Notification upload could not be completed right now.", 500)
    return (
        jsonify(
            {
                "ok": True,
                "message": _message_payload(records[0]),
                "messages": [_message_payload(record) for record in records],
                "ingested_count": len(records),
                "skipped_suppressed_count": skipped_suppressed,
                "device": _notification_device_payload(device),
                "parent_alert_email_sent": any(item["email_sent"] for item in parent_alerts),
                "parent_alerts": parent_alerts,
            }
        ),
        201,
    )


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

    payload = request.get_json(silent=True) or {}
    message_text = str(payload.get("message_text", "")).strip()
    source_platform = str(payload.get("source_platform", "social media")).strip() or "social media"
    sender_handle = str(payload.get("sender_handle", "")).strip() or None
    browser_origin = str(payload.get("browser_origin", "")).strip() or None

    if not message_text:
        return _error("Message text is required.")
    if is_message_suppressed(
        family_id=current_user.family_id,
        child_user_id=current_user.id,
        message_text=message_text,
    ):
        return jsonify(
            {
                "ok": True,
                "ignored": True,
                "message": "This message was already removed by the parent/guardian.",
            }
        ), 202

    try:
        prediction = predict_message(
            message_text,
            family_id=current_user.family_id,
            source_platform=source_platform,
            sender_handle=sender_handle,
        )
    except PredictionUnavailable as exc:
        return _error(str(exc), 503)
    verification = verify_message(message_text, prediction.label)

    record = MessageRecord(
        family_id=current_user.family_id,
        submitted_by_id=current_user.id,
        source_platform=source_platform,
        sender_handle=sender_handle,
        browser_origin=browser_origin,
        message_text=message_text,
        review_signature=build_review_signature(message_text),
        predicted_label=prediction.label,
        predicted_confidence=prediction.confidence,
        risk_indicators=prediction.risk_indicators,
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
    parent_user = User.query.filter_by(family_id=current_user.family_id, role="parent").first()
    email_alert_sent, email_alert_message = send_high_risk_message_alert(parent_user, current_user, record)
    if email_alert_sent and parent_user:
        log_event(
            current_user.family_id,
            parent_user.id,
            "parent_alert_emailed",
            f"Parent alert email sent for message {record.id}.",
            subject_user_id=current_user.id,
        )
    db.session.commit()
    return jsonify(
        {
            "ok": True,
            "message": _message_payload(record),
            "parent_alert_email_sent": email_alert_sent,
            "parent_alert_email_message": email_alert_message,
        }
    ), 201


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
    parent_user = User.query.filter_by(family_id=current_user.family_id, role="parent").first()
    email_alert_sent, email_alert_message = send_logout_request_alert(parent_user, current_user, logout_request)
    if email_alert_sent and parent_user:
        log_event(
            current_user.family_id,
            parent_user.id,
            "parent_alert_emailed",
            f"Parent alert email sent for logout request {logout_request.id}.",
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
                "parent_alert_email_sent": email_alert_sent,
                "parent_alert_email_message": email_alert_message,
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
