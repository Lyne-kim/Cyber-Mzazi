from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import ActivityLog, LogoutRequest, MessageRecord
from .services.audit import log_event


parent_bp = Blueprint("parent", __name__, url_prefix="/parent")


@parent_bp.before_request
@login_required
def require_parent():
    if current_user.role != "parent":
        flash("Parent access only.", "danger")
        return redirect(url_for("child.dashboard"))
    return None


@parent_bp.route("/dashboard")
def dashboard():
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
    return render_template(
        "parent_dashboard.html",
        messages=messages,
        logout_requests=logout_requests,
        activity_logs=activity_logs,
    )


@parent_bp.post("/messages/<int:message_id>/review")
def review_message(message_id: int):
    record = MessageRecord.query.filter_by(
        id=message_id, family_id=current_user.family_id
    ).first_or_404()
    reviewed_label = request.form.get("reviewed_label", "").strip()
    if not reviewed_label:
        flash("Choose a reviewed label.", "warning")
        return redirect(url_for("parent.dashboard"))

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
    return redirect(url_for("parent.dashboard"))


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
        f"Approved sign-out for child user {logout_request.child_user_id}",
    )
    db.session.commit()
    flash("Logout approved. The child can now sign out once.", "success")
    return redirect(url_for("parent.dashboard"))
