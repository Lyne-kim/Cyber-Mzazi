from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import LogoutRequest, MessageRecord
from .services.audit import log_event
from .services.ml_service import get_classifier
from .services.verification import verify_message


child_bp = Blueprint("child", __name__, url_prefix="/child")


@child_bp.before_request
@login_required
def require_child():
    if current_user.role != "child":
        flash("Child access only.", "danger")
        return redirect(url_for("parent.dashboard"))
    return None


@child_bp.route("/dashboard")
def dashboard():
    messages = (
        MessageRecord.query.filter_by(family_id=current_user.family_id)
        .order_by(MessageRecord.created_at.desc())
        .limit(10)
        .all()
    )
    pending_logout = LogoutRequest.query.filter_by(
        family_id=current_user.family_id, child_user_id=current_user.id, status="pending"
    ).first()
    return render_template(
        "child_dashboard.html", messages=messages, pending_logout=pending_logout
    )


@child_bp.post("/messages")
def submit_message():
    classifier = get_classifier()
    if classifier is None:
        flash("Train the model first with `flask train-models`.", "danger")
        return redirect(url_for("child.dashboard"))

    message_text = request.form.get("message_text", "").strip()
    source_platform = request.form.get("source_platform", "").strip() or "manual"
    sender_handle = request.form.get("sender_handle", "").strip()
    browser_origin = request.form.get("browser_origin", "").strip()

    if not message_text:
        flash("Enter a message before submitting.", "warning")
        return redirect(url_for("child.dashboard"))

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
        f"Submitted {source_platform} message for analysis",
    )
    db.session.commit()
    flash("Message analysed and saved to the family dashboard.", "success")
    return redirect(url_for("child.dashboard"))
