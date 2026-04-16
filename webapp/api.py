from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from .extensions import db
from .models import ActivityLog, Family, LogoutRequest, MessageRecord, User
from .services.audit import log_event
from .services.ml_service import get_classifier
from .services.verification import verify_message


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
    }


def _message_payload(message: MessageRecord) -> dict:
    return {
        "id": message.id,
        "source_platform": message.source_platform,
        "sender_handle": message.sender_handle,
        "browser_origin": message.browser_origin,
        "message_text": message.message_text,
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


def _log_payload(log: ActivityLog) -> dict:
    return {
        "id": log.id,
        "event_type": log.event_type,
        "details": log.details,
        "created_at": log.created_at.isoformat(),
        "actor_id": log.actor_id,
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
    )
    parent_user.set_password(str(payload["parent_password"]))

    child_user = User(
        family=family,
        role="child",
        name=str(payload["child_name"]).strip(),
        username=child_username,
        logout_requires_parent_approval=True,
    )
    child_user.set_password(str(payload["child_password"]))

    db.session.add_all([family, parent_user, child_user])
    db.session.flush()
    log_event(family.id, parent_user.id, "family_registered", "Family account created via API")
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
    log_event(user.family_id, user.id, "login", f"{user.role} logged in via API")
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
    log_event(family_id, actor_id, "logout", f"{role} logged out via API")
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

    messages = (
        MessageRecord.query.filter_by(family_id=current_user.family_id)
        .order_by(MessageRecord.created_at.desc())
        .limit(20)
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
        .limit(30)
        .all()
    )
    return jsonify(
        {
            "ok": True,
            "messages": [_message_payload(message) for message in messages],
            "logout_requests": [
                {
                    "id": item.id,
                    "child_user_id": item.child_user_id,
                    "status": item.status,
                    "created_at": item.created_at.isoformat(),
                }
                for item in logout_requests
            ],
            "activity_logs": [_log_payload(log) for log in activity_logs],
        }
    )


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
        f"Approved sign-out for child user {logout_request.child_user_id} via API",
    )
    db.session.commit()
    return jsonify({"ok": True})


@api_bp.get("/child/dashboard")
@login_required
def child_dashboard():
    if current_user.role != "child":
        return _error("Child access only.", 403)

    messages = (
        MessageRecord.query.filter_by(family_id=current_user.family_id)
        .order_by(MessageRecord.created_at.desc())
        .limit(15)
        .all()
    )
    pending_logout = LogoutRequest.query.filter_by(
        family_id=current_user.family_id,
        child_user_id=current_user.id,
        status="pending",
    ).first()
    return jsonify(
        {
            "ok": True,
            "messages": [_message_payload(message) for message in messages],
            "pending_logout": None
            if pending_logout is None
            else {
                "id": pending_logout.id,
                "status": pending_logout.status,
                "created_at": pending_logout.created_at.isoformat(),
            },
        }
    )


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
    source_platform = str(payload.get("source_platform", "manual")).strip() or "manual"
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
        f"Submitted {source_platform} message for analysis via API",
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

    logout_request = LogoutRequest(
        family_id=current_user.family_id,
        child_user_id=current_user.id,
        status="pending",
    )
    db.session.add(logout_request)
    log_event(
        current_user.family_id,
        current_user.id,
        "logout_requested",
        "Child requested sign-out approval via API",
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
