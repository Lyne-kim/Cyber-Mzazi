from __future__ import annotations

import re
from difflib import SequenceMatcher

from flask import current_app

from ml.labels import RISK_TERMS

from ..models import MessageRecord


def normalize_review_text(text: str | None) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "").strip().lower())
    return normalized


def build_review_signature(text: str | None) -> str:
    return normalize_review_text(text)[:512]


def find_review_feedback(text: str, family_id: int | None = None) -> dict | None:
    if not current_app.config.get("ENABLE_REVIEW_FEEDBACK_MATCHING", True):
        return None

    signature = build_review_signature(text)
    if not signature:
        return None

    base_query = MessageRecord.query.filter(MessageRecord.reviewed_label.isnot(None))
    if family_id is not None:
        base_query = base_query.filter_by(family_id=family_id)

    exact_match = (
        base_query.filter_by(review_signature=signature)
        .order_by(MessageRecord.updated_at.desc())
        .first()
    )
    if exact_match is not None:
        label = exact_match.reviewed_label
        return {
            "label": label,
            "confidence": 0.99,
            "risk_indicators": ",".join(RISK_TERMS.get(label, ["review"])),
            "provider": "review_feedback",
            "match_type": "exact",
            "matched_message_id": exact_match.id,
        }

    threshold = float(current_app.config.get("REVIEW_FEEDBACK_SIMILARITY_THRESHOLD", 0.92))
    lookback = int(current_app.config.get("REVIEW_FEEDBACK_LOOKBACK", 200))
    candidates = (
        base_query.order_by(MessageRecord.updated_at.desc())
        .limit(lookback)
        .all()
    )

    best_match = None
    best_score = 0.0
    for candidate in candidates:
        candidate_signature = candidate.review_signature or build_review_signature(candidate.message_text)
        if not candidate_signature:
            continue
        score = SequenceMatcher(a=signature, b=candidate_signature).ratio()
        if score >= threshold and score > best_score:
            best_score = score
            best_match = candidate

    if best_match is None:
        return None

    label = best_match.reviewed_label
    return {
        "label": label,
        "confidence": max(best_score, 0.85),
        "risk_indicators": ",".join(RISK_TERMS.get(label, ["review"])),
        "provider": "review_feedback",
        "match_type": "similar",
        "matched_message_id": best_match.id,
    }
