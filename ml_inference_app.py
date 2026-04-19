from __future__ import annotations

from flask import Flask, jsonify, request

from config import Config
from webapp.services.ml_service import get_classifier


def create_ml_inference_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    def _is_authorized() -> bool:
        expected = app.config.get("MODEL_INFERENCE_TOKEN", "").strip()
        if not expected:
            return True
        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip() == expected
        return False

    @app.get("/health")
    def health():
        classifier = get_classifier()
        return jsonify(
            {
                "ok": True,
                "service": "cyber-mzazi-ml",
                "model_loaded": classifier is not None,
                "artifact_path": app.config["MODEL_ARTIFACT_PATH"],
            }
        )

    @app.post("/predict")
    def predict():
        if not _is_authorized():
            return jsonify({"ok": False, "error": "Unauthorized"}), 401

        payload = request.get_json(silent=True) or {}
        text = str(payload.get("text", "")).strip()
        if not text:
            return jsonify({"ok": False, "error": "Text is required."}), 400

        classifier = get_classifier()
        if classifier is None:
            return jsonify({"ok": False, "error": "Model is not ready."}), 503

        prediction = classifier.predict(text)
        return jsonify(
            {
                "ok": True,
                "prediction": {
                    "label": prediction["label"],
                    "confidence": float(prediction["confidence"]),
                    "risk_indicators": prediction["risk_indicators"],
                },
            }
        )

    return app
