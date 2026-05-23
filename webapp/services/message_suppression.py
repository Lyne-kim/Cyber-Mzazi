from __future__ import annotations

from ..extensions import db
from ..models import DeletedMessageSignature, MessageRecord
from .review_feedback import build_review_signature


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def suppress_message(record: MessageRecord, deleted_by_id: int | None) -> DeletedMessageSignature:
    signature = record.review_signature or build_review_signature(record.message_text)
    existing = DeletedMessageSignature.query.filter_by(
        family_id=record.family_id,
        child_user_id=record.submitted_by_id,
        review_signature=signature,
    ).first()
    if existing:
        existing.deleted_by_id = deleted_by_id or existing.deleted_by_id
        existing.source_platform = _clean(record.source_platform) or existing.source_platform
        existing.source_app_package = _clean(record.source_app_package) or existing.source_app_package
        existing.sender_handle = _clean(record.sender_handle) or existing.sender_handle
        existing.notification_title = _clean(record.notification_title) or existing.notification_title
        existing.message_excerpt = (record.message_text or "")[:500]
        db.session.add(existing)
        return existing

    suppression = DeletedMessageSignature(
        family_id=record.family_id,
        child_user_id=record.submitted_by_id,
        deleted_by_id=deleted_by_id,
        review_signature=signature,
        source_platform=_clean(record.source_platform),
        source_app_package=_clean(record.source_app_package),
        sender_handle=_clean(record.sender_handle),
        notification_title=_clean(record.notification_title),
        message_excerpt=(record.message_text or "")[:500],
    )
    db.session.add(suppression)
    return suppression


def is_message_suppressed(
    *,
    family_id: int,
    child_user_id: int,
    message_text: str,
) -> bool:
    signature = build_review_signature(message_text)
    return bool(
        DeletedMessageSignature.query.filter_by(
            family_id=family_id,
            child_user_id=child_user_id,
            review_signature=signature,
        ).first()
    )
