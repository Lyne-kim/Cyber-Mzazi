from __future__ import annotations

import secrets

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from sqlalchemy import func

from .extensions import db
from .models import (
    ActivityLog,
    DeletedMessageSignature,
    MessageRecord,
    NotificationIngestionDevice,
)
from .services.prediction_service import prediction_backend_status


developer_bp = Blueprint("developer", __name__, url_prefix="/developer")


def _developer_token() -> str:
    return str(current_app.config.get("DEVELOPER_STATUS_TOKEN", "")).strip()


def _developer_authenticated() -> bool:
    expected = _developer_token()
    if not expected:
        return False
    supplied = str(session.get("developer_token", "")).strip()
    query_token = request.args.get("token", "").strip()
    if query_token and secrets.compare_digest(query_token, expected):
        session["developer_token"] = query_token
        return True
    return bool(supplied and secrets.compare_digest(supplied, expected))


def _require_developer():
    if _developer_authenticated():
        return None
    return redirect(url_for("developer.login", next=request.path))


@developer_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        token = request.form.get("developer_token", "").strip()
        expected = _developer_token()
        if expected and secrets.compare_digest(token, expected):
            session["developer_token"] = token
            flash("Developer console unlocked.", "success")
            return redirect(request.form.get("next") or url_for("developer.dashboard"))
        flash("Developer token is invalid.", "danger")
    return render_template("developer_console.html", mode="login")


@developer_bp.post("/logout")
def logout():
    session.pop("developer_token", None)
    flash("Developer console locked.", "success")
    return redirect(url_for("developer.login"))


@developer_bp.get("/")
def dashboard():
    guard = _require_developer()
    if guard:
        return guard

    label_rows = (
        db.session.query(MessageRecord.predicted_label, func.count(MessageRecord.id))
        .group_by(MessageRecord.predicted_label)
        .order_by(func.count(MessageRecord.id).desc())
        .all()
    )
    status = {
        "model": prediction_backend_status(),
        "message_count": MessageRecord.query.count(),
        "suppressed_count": DeletedMessageSignature.query.count(),
        "device_count": NotificationIngestionDevice.query.count(),
        "recent_failures": ActivityLog.query.filter(ActivityLog.details.ilike("%failed%"))
        .order_by(ActivityLog.created_at.desc())
        .limit(5)
        .all(),
        "label_rows": label_rows,
    }
    return render_template(
        "developer_console.html",
        mode="dashboard",
        status=status,
    )
