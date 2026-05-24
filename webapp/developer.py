from __future__ import annotations

import secrets

from io import BytesIO

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, session, url_for
from sqlalchemy import func
from werkzeug.utils import secure_filename

from .extensions import db
from .models import (
    ActivityLog,
    DeletedMessageSignature,
    MessageRecord,
    NotificationIngestionDevice,
    SafetyResourceDocument,
    SafetyResourceLink,
    SafetyResourceRequest,
)
from .services.prediction_service import prediction_backend_status
from .services.resource_library import rebuild_document_chunks


developer_bp = Blueprint("developer", __name__, url_prefix="/developer")

MAX_DEVELOPER_RESOURCE_BYTES = 8 * 1024 * 1024


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

    documents = SafetyResourceDocument.query.order_by(SafetyResourceDocument.created_at.desc()).all()
    links = SafetyResourceLink.query.order_by(SafetyResourceLink.created_at.desc()).all()
    requests = SafetyResourceRequest.query.order_by(SafetyResourceRequest.created_at.desc()).all()
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
        documents=documents,
        links=links,
        requests=requests,
        status=status,
    )


@developer_bp.post("/safety-resources/documents")
def upload_documents():
    guard = _require_developer()
    if guard:
        return guard

    uploads = [upload for upload in request.files.getlist("attachments") if upload and upload.filename]
    if not uploads:
        flash("Choose at least one book or document.", "warning")
        return redirect(url_for("developer.dashboard"))

    title = request.form.get("title", "").strip()
    topic = request.form.get("topic", "").strip() or "Digital safety"
    audience = request.form.get("audience", "all").strip().lower()
    summary = request.form.get("summary", "").strip()
    source_url = request.form.get("source_url", "").strip()
    visibility = request.form.get("visibility", "all").strip().lower()
    request_id = request.form.get("request_id", type=int)
    related_request = SafetyResourceRequest.query.get(request_id) if request_id else None
    family_id = related_request.family_id if visibility == "request_family" and related_request else None
    cover_upload = request.files.get("cover_image")
    cover_data = cover_upload.read() if cover_upload and cover_upload.filename else None
    if audience not in {"all", "parent", "child"}:
        audience = "all"
    if cover_data and len(cover_data) > MAX_DEVELOPER_RESOURCE_BYTES:
        flash("Cover image is too large. Maximum size is 8 MB.", "danger")
        return redirect(url_for("developer.dashboard"))

    uploaded_count = 0
    for upload in uploads:
        binary_data = upload.read()
        filename = secure_filename(upload.filename) or "resource-document"
        if len(binary_data) > MAX_DEVELOPER_RESOURCE_BYTES:
            flash(f"{filename} is too large. Maximum size is 8 MB.", "danger")
            continue
        document = SafetyResourceDocument(
            family_id=family_id,
            uploaded_by_id=None,
            filename=filename,
            content_type=upload.mimetype,
            file_size=len(binary_data),
            binary_data=binary_data,
            title=title or filename,
            topic=topic,
            audience=audience,
            summary=summary,
            source_url=source_url or None,
            cover_filename=secure_filename(cover_upload.filename) if cover_data and cover_upload else None,
            cover_content_type=cover_upload.mimetype if cover_data and cover_upload else None,
            cover_binary_data=cover_data,
            status="approved",
        )
        db.session.add(document)
        db.session.flush()
        rebuild_document_chunks(document)
        uploaded_count += 1
    if related_request and uploaded_count:
        related_request.status = "fulfilled"
    db.session.commit()
    flash(f"{uploaded_count} resource document(s) uploaded.", "success")
    return redirect(url_for("developer.dashboard"))


@developer_bp.post("/safety-resources/links")
def add_link():
    guard = _require_developer()
    if guard:
        return guard

    title = request.form.get("title", "").strip()
    resource_url = request.form.get("url", "").strip()
    topic = request.form.get("topic", "").strip() or "Digital safety"
    audience = request.form.get("audience", "all").strip().lower()
    summary = request.form.get("summary", "").strip()
    if audience not in {"all", "parent", "child"}:
        audience = "all"
    if not title or not resource_url.startswith(("https://", "http://")):
        flash("Enter a title and a valid web URL.", "warning")
        return redirect(url_for("developer.dashboard"))

    link = SafetyResourceLink(
        family_id=None,
        created_by_id=None,
        title=title,
        url=resource_url,
        topic=topic,
        audience=audience,
        summary=summary,
        status="approved",
    )
    db.session.add(link)
    db.session.commit()
    flash("Resource link added.", "success")
    return redirect(url_for("developer.dashboard"))


@developer_bp.post("/safety-resources/requests/<int:request_id>/status")
def update_request_status(request_id: int):
    guard = _require_developer()
    if guard:
        return guard

    item = SafetyResourceRequest.query.get_or_404(request_id)
    status = request.form.get("status", "").strip().lower()
    if status not in {"pending", "approved", "rejected", "fulfilled"}:
        flash("Choose a valid request status.", "warning")
        return redirect(url_for("developer.dashboard"))
    item.status = status
    db.session.commit()
    flash("Resource request updated.", "success")
    return redirect(url_for("developer.dashboard"))


@developer_bp.post("/safety-resources/documents/<int:document_id>/delete")
def delete_document(document_id: int):
    guard = _require_developer()
    if guard:
        return guard

    document = SafetyResourceDocument.query.get_or_404(document_id)
    db.session.delete(document)
    db.session.commit()
    flash("Resource document deleted.", "success")
    return redirect(url_for("developer.dashboard"))


@developer_bp.get("/safety-resources/documents/<int:document_id>/cover")
def document_cover(document_id: int):
    guard = _require_developer()
    if guard:
        return guard

    document = SafetyResourceDocument.query.get_or_404(document_id)
    if not document.cover_binary_data:
        return "", 404
    return send_file(
        BytesIO(document.cover_binary_data),
        mimetype=document.cover_content_type or "image/png",
        download_name=document.cover_filename or f"resource-{document.id}-cover",
    )


@developer_bp.post("/safety-resources/links/<int:link_id>/delete")
def delete_link(link_id: int):
    guard = _require_developer()
    if guard:
        return guard

    link = SafetyResourceLink.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    flash("Resource link deleted.", "success")
    return redirect(url_for("developer.dashboard"))
