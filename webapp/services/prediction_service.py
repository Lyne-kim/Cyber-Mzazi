from __future__ import annotations

from dataclasses import dataclass

import requests
from flask import current_app

from .ml_service import get_classifier


@dataclass
class PredictionResult:
    label: str
    confidence: float
    risk_indicators: str
    provider: str


class PredictionUnavailable(RuntimeError):
    pass


def prediction_backend_status() -> dict:
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


def predict_message(text: str) -> PredictionResult:
    model_api_url = current_app.config.get("MODEL_API_URL", "").strip()
    if model_api_url:
        headers = {"Content-Type": "application/json"}
        token = current_app.config.get("MODEL_API_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = requests.post(
                model_api_url,
                json={"text": text},
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            prediction = payload.get("prediction") or {}
            return PredictionResult(
                label=str(prediction.get("label", "safe")),
                confidence=float(prediction.get("confidence", 0.0)),
                risk_indicators=str(prediction.get("risk_indicators", "")),
                provider="remote",
            )
        except (requests.RequestException, ValueError, TypeError) as exc:
            raise PredictionUnavailable(f"Remote model request failed: {exc}") from exc

    classifier = get_classifier()
    if classifier is None:
        raise PredictionUnavailable("Model is not ready.")
    prediction = classifier.predict(text)
    return PredictionResult(
        label=prediction["label"],
        confidence=float(prediction["confidence"]),
        risk_indicators=prediction["risk_indicators"],
        provider="local",
    )
