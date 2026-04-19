from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import LogoutRequest, MessageRecord
from .services.audit import log_event
from .services.parent_alerts import send_high_risk_message_alert
from .services.prediction_service import PredictionUnavailable, predict_message
from .services.verification import verify_message
from .ui_text import SUPPORTED_LANGUAGES


child_bp = Blueprint("child", __name__, url_prefix="/child")


CHILD_NAV_ITEMS = [
    {"endpoint": "child.dashboard", "icon": "&#127968;", "label": "Home", "key": "home"},
    {"endpoint": "child.my_safety", "icon": "&#128737;", "label": "My Safety", "key": "my_safety"},
    {"endpoint": "child.talk", "icon": "&#128172;", "label": "Talk", "key": "talk"},
    {"endpoint": "child.help_questions", "icon": "&#10067;", "label": "Help", "key": "help"},
    {"endpoint": "child.settings", "icon": "&#9881;", "label": "Settings", "key": "settings"},
]


@child_bp.before_request
@login_required
def require_child():
    if current_user.role != "child":
        flash("Child access only.", "danger")
        return redirect(url_for("parent.dashboard"))
    return None


def _child_data() -> dict:
    messages = (
        MessageRecord.query.filter_by(family_id=current_user.family_id)
        .order_by(MessageRecord.created_at.desc())
        .limit(10)
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
        "messages": messages,
        "pending_logout": pending_logout,
    }


def _render_child_page(page_key: str, page_title: str) -> str:
    context = _child_data()
    return render_template(
        "child_page.html",
        page_key=page_key,
        page_title=page_title,
        child_nav_items=CHILD_NAV_ITEMS,
        **context,
    )


@child_bp.route("/dashboard")
def dashboard():
    return _render_child_page("home", "Home")


@child_bp.route("/my-safety")
def my_safety():
    return _render_child_page("my_safety", "My Safety")


@child_bp.route("/talk")
def talk():
    return _render_child_page("talk", "Talk to Grown-up")


@child_bp.route("/help")
def help_questions():
    return _render_child_page("help", "Help & Questions")


@child_bp.route("/settings")
def settings():
    return _render_child_page("settings", "Settings")


@child_bp.route("/report")
def report():
    return _render_child_page("report", "Safety Check")


@child_bp.post("/language")
def set_language():
    language = request.form.get("language", "en").strip().lower()
    if language not in SUPPORTED_LANGUAGES:
        flash("Choose English or Swahili.", "warning")
        return redirect(url_for("child.settings"))

    session["ui_language"] = language
    current_user.preferred_language = language
    log_event(
        current_user.family_id,
        current_user.id,
        "language_changed",
        f"Child interface language set to {SUPPORTED_LANGUAGES[language]}",
        subject_user_id=current_user.id,
    )
    db.session.commit()
    flash(f"Language updated to {SUPPORTED_LANGUAGES[language]}.", "success")
    return redirect(request.form.get("next") or url_for("child.settings"))


@child_bp.post("/messages")
def submit_message():
    message_text = request.form.get("message_text", "").strip()
    source_platform = request.form.get("source_platform", "").strip() or "social media"
    sender_handle = request.form.get("sender_handle", "").strip()
    browser_origin = request.form.get("browser_origin", "").strip()

    if not message_text:
        flash("Enter a message before submitting.", "warning")
        return redirect(url_for("child.report"))

    try:
        prediction = predict_message(message_text)
    except PredictionUnavailable as exc:
        flash(str(exc), "danger")
        return redirect(url_for("child.report"))
    verification = verify_message(message_text, prediction.label)

    record = MessageRecord(
        family_id=current_user.family_id,
        submitted_by_id=current_user.id,
        source_platform=source_platform,
        sender_handle=sender_handle,
        browser_origin=browser_origin,
        message_text=message_text,
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
        f"Flagged an incoming message from {source_platform} for safety analysis",
        subject_user_id=current_user.id,
    )
    parent_user = current_user.family.users.filter_by(role="parent").first()
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
    if email_alert_sent:
        flash("Incoming message analysed and parent/guardian email alert sent.", "success")
    else:
        flash("Incoming message analysed and shared with the family safety dashboard.", "success")
    return redirect(url_for("child.report"))
