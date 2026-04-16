from __future__ import annotations

from functools import lru_cache

import joblib
import numpy as np
from flask import current_app


class MessageClassifier:
    def __init__(self, artifact_path: str):
        artifact = joblib.load(artifact_path)
        self.vectorizer = artifact["vectorizer"]
        self.svd = artifact["svd"]
        self.linear_model = artifact["linear_model"]
        self.rf_model = artifact["rf_model"]
        self.classes = artifact["classes"]

    @staticmethod
    def _softmax(scores: np.ndarray) -> np.ndarray:
        scores = scores - np.max(scores, axis=1, keepdims=True)
        exp_scores = np.exp(scores)
        return exp_scores / exp_scores.sum(axis=1, keepdims=True)

    def predict(self, text: str) -> dict:
        transformed = self.vectorizer.transform([text])
        dense = self.svd.transform(transformed)

        linear_scores = np.clip(self.linear_model.predict(dense), 1e-9, None)
        linear_probs = self._softmax(linear_scores)
        rf_probs = self.rf_model.predict_proba(dense)
        rf_prob_matrix = np.vstack(rf_probs).T if isinstance(rf_probs, list) else rf_probs

        blended = (0.45 * linear_probs) + (0.55 * rf_prob_matrix)
        top_index = int(np.argmax(blended[0]))
        label = self.classes[top_index]

        risk_terms = {
            "grooming": ["trust_building", "secrecy", "meetup_language"],
            "betting": ["financial_pressure", "false_promises", "gambling"],
            "sextortion": ["coercion", "image_request", "threat_language"],
            "safe": ["none"],
        }
        return {
            "label": label,
            "confidence": float(blended[0][top_index]),
            "risk_indicators": ",".join(risk_terms.get(label, ["review"])),
        }


@lru_cache(maxsize=1)
def get_classifier() -> MessageClassifier | None:
    artifact_path = current_app.config["MODEL_ARTIFACT_PATH"]
    try:
        return MessageClassifier(artifact_path)
    except FileNotFoundError:
        return None
