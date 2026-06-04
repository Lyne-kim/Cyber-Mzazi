from __future__ import annotations

from dataclasses import dataclass

import requests
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from ml.labels import LABEL_HINTS, RISK_TERMS, SAFE_LABEL, normalize_label
from ml.safe_overrides import safe_message_override, split_config_list

from .ml_service import get_classifier
from .review_feedback import find_review_feedback


@dataclass
class PredictionResult:
    label: str
    confidence: float
    risk_indicators: str
    provider: str


class PredictionUnavailable(RuntimeError):
    pass


COMMERCE_SAFE_TERMS = {
    "offer",
    "offers",
    "sale",
    "discount",
    "shop",
    "shopping",
    "dress",
    "wallet",
    "deodorant",
    "delivery",
    "cart",
    "order",
    "promo",
    "kilimall",
    "jumia",
}


def _has_supported_risk_hint(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(keyword in lowered for keywords in LABEL_HINTS.values() for keyword in keywords)


def _looks_like_low_risk_commerce(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(term in lowered for term in COMMERCE_SAFE_TERMS)


def _sanitize_prediction(text: str, label: object, confidence: object, risk_indicators: object) -> PredictionResult:
    raw_label = str(label or "").strip().lower()
    normalized = normalize_label(raw_label)
    try:
        safe_confidence = float(confidence)
    except (TypeError, ValueError):
        safe_confidence = 0.0

    if (
        raw_label != normalized
        or (normalized != SAFE_LABEL and safe_confidence < 0.5)
    ):
        classifier = get_classifier()
        heuristic = classifier.predict(text) if classifier is not None else {
            "label": SAFE_LABEL,
            "confidence": 0.0,
            "risk_indicators": "none",
        }
        normalized = normalize_label(heuristic.get("label"))
        safe_confidence = float(heuristic.get("confidence", safe_confidence))
        risk_indicators = heuristic.get("risk_indicators", risk_indicators)

    if (
        normalized != SAFE_LABEL
        and safe_confidence < 0.78
        and _looks_like_low_risk_commerce(text)
        and not _has_supported_risk_hint(text)
    ):
        normalized = SAFE_LABEL
        safe_confidence = max(safe_confidence, 0.72)
        risk_indicators = ",".join(RISK_TERMS[SAFE_LABEL])

    return PredictionResult(
        label=normalized,
        confidence=safe_confidence,
        risk_indicators=str(risk_indicators or ",".join(RISK_TERMS.get(normalized, ["review"]))),
        provider="",
    )


def _fallback_prediction(text: str, reason: str) -> PredictionResult:
    classifier = None
    if current_app.config.get("ENABLE_HEURISTIC_FALLBACK", True):
        try:
            classifier = get_classifier()
        except Exception as exc:  # pragma: no cover - defensive fallback path
            current_app.logger.warning("Classifier fallback unavailable after %s: %s", reason, exc)

    if classifier is not None:
        try:
            prediction = classifier.predict(text)
            return PredictionResult(
                label=normalize_label(prediction.get("label")),
                confidence=float(prediction.get("confidence", 0.0)),
                risk_indicators=str(prediction.get("risk_indicators") or ",".join(RISK_TERMS.get(SAFE_LABEL, ["none"]))),
                provider="heuristic_fallback",
            )
        except Exception as exc:  # pragma: no cover - defensive fallback path
            current_app.logger.warning("Heuristic fallback prediction failed after %s: %s", reason, exc)

    return PredictionResult(
        label=SAFE_LABEL,
        confidence=0.0,
        risk_indicators="prediction_unavailable",
        provider="safe_fallback",
    )


def prediction_backend_status() -> dict:
    provider = current_app.config.get("MODEL_PROVIDER", "auto")
    if provider == "heuristic":
        return {
            "provider": "heuristic",
            "configured": True,
            "model_loaded": True,
            "endpoint": None,
        }

    model_api_url = current_app.config.get("MODEL_API_URL", "").strip()
    if model_api_url:
        return {
            "provider": "remote",
            "configured": True,
            "model_loaded": True,
            "endpoint": model_api_url,
        }

    classifier = get_classifier()
    return {
        "provider": "local",
        "configured": classifier is not None,
        "model_loaded": classifier is not None,
        "endpoint": None,
    }


def predict_message(
    text: str,
    family_id: int | None = None,
    *,
    source_platform: str | None = None,
    sender_handle: str | None = None,
    app_package: str | None = None,
    notification_title: str | None = None,
) -> PredictionResult:
    safe_override = safe_message_override(
        text,
        source_platform=source_platform,
        sender_handle=sender_handle,
        app_package=app_package,
        notification_title=notification_title,
        extra_prefixes=split_config_list(current_app.config.get("SAFE_MESSAGE_PREFIXES", "")),
        extra_source_patterns=split_config_list(current_app.config.get("SAFE_SENDER_PATTERNS", "")),
        extra_link_domains=split_config_list(current_app.config.get("SAFE_LINK_DOMAINS", "")),
    )
    if safe_override is not None:
        return PredictionResult(
            label=SAFE_LABEL,
            confidence=float(safe_override["confidence"]),
            risk_indicators=str(safe_override["risk_indicators"]),
            provider="safe_override",
        )

    try:
        review_feedback = find_review_feedback(text, family_id=family_id)
    except SQLAlchemyError as exc:
        current_app.logger.warning("Review feedback lookup skipped: %s", exc)
        review_feedback = None
    if review_feedback is not None:
        return PredictionResult(
            label=normalize_label(str(review_feedback["label"])),
            confidence=float(review_feedback["confidence"]),
            risk_indicators=str(review_feedback["risk_indicators"]),
            provider=str(review_feedback["provider"]),
        )

    provider = current_app.config.get("MODEL_PROVIDER", "auto")
    if provider == "heuristic":
        classifier = get_classifier()
        prediction = classifier.predict(text) if classifier is not None else {
            "label": "safe",
            "confidence": 0.0,
            "risk_indicators": "none",
        }
        return PredictionResult(
            label=normalize_label(str(prediction["label"])),
            confidence=float(prediction["confidence"]),
            risk_indicators=str(prediction["risk_indicators"]),
            provider="heuristic",
        )

    model_api_url = current_app.config.get("MODEL_API_URL", "").strip()
    if model_api_url:
        headers = {"Content-Type": "application/json"}
        token = current_app.config.get("MODEL_API_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = requests.post(
                model_api_url,
                json={
                    "text": text,
                    "source_platform": source_platform,
                    "sender_handle": sender_handle,
                    "app_package": app_package,
                    "notification_title": notification_title,
                },
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            prediction = payload.get("prediction") or {}
            sanitized = _sanitize_prediction(
                text,
                prediction.get("label", SAFE_LABEL),
                prediction.get("confidence", 0.0),
                prediction.get("risk_indicators", ""),
            )
            sanitized.provider = "remote"
            return sanitized
        except (requests.RequestException, ValueError, TypeError) as exc:
            current_app.logger.exception("Remote model request failed; using fallback prediction.")
            return _fallback_prediction(text, f"remote model request failed: {exc}")

    try:
        classifier = get_classifier()
        if classifier is None:
            raise PredictionUnavailable("Model is not ready.")
        prediction = classifier.predict(text)
        sanitized = _sanitize_prediction(
            text,
            prediction.get("label", SAFE_LABEL),
            prediction.get("confidence", 0.0),
            prediction.get("risk_indicators", ""),
        )
        sanitized.provider = "local"
        return sanitized
    except Exception as exc:
        current_app.logger.exception("Local prediction failed; using fallback prediction.")
        return _fallback_prediction(text, f"local prediction failed: {exc}")
