from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import LogoutRequest, MessageRecord
from .services.audit import log_event
from .services.ml_service import get_classifier
from .services.verification import verify_message


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
    pending_logout = LogoutRequest.query.filter_by(
        family_id=current_user.family_id, child_user_id=current_user.id, status="pending"
    ).first()
    return {"messages": messages, "pending_logout": pending_logout}


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


@child_bp.post("/messages")
def submit_message():
    classifier = get_classifier()
    if classifier is None:
        flash("Train the model first with `flask train-models`.", "danger")
        return redirect(url_for("child.report"))

    message_text = request.form.get("message_text", "").strip()
    source_platform = request.form.get("source_platform", "").strip() or "social media"
    sender_handle = request.form.get("sender_handle", "").strip()
    browser_origin = request.form.get("browser_origin", "").strip()

    if not message_text:
        flash("Enter a message before submitting.", "warning")
        return redirect(url_for("child.report"))

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
        f"Flagged an incoming message from {source_platform} for safety analysis",
    )
    db.session.commit()
    flash("Incoming message analysed and shared with the family safety dashboard.", "success")
    return redirect(url_for("child.report"))
