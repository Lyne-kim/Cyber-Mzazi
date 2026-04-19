from __future__ import annotations

import json
from functools import lru_cache

from flask import current_app

from ml.artifacts import resolve_legacy_artifact_file, resolve_transformer_artifact_dir
from ml.labels import LABEL_HINTS, RISK_TERMS, SAFE_LABEL, SUPPORTED_LABELS


class MessageClassifier:
    HIGH_SIGNAL_HINT_LABELS = {
        "phishing",
        "financial_fraud",
        "grooming",
        "sextortion",
        "violence",
        "hate_speech",
        "cyberbullying",
        "misinformation",
    }

    def __init__(self, artifact_path: str):
        self.risk_terms = RISK_TERMS
        transformer_dir = resolve_transformer_artifact_dir(artifact_path)
        if transformer_dir.is_dir() and (transformer_dir / "config.json").exists():
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self.backend = "transformer"
            metadata = json.loads((transformer_dir / "metadata.json").read_text(encoding="utf-8"))
            self.max_length = int(metadata.get("max_length", 160))
            self.classes = metadata["classes"]
            self.torch = torch
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.tokenizer = AutoTokenizer.from_pretrained(transformer_dir, use_fast=False)
            self.model = AutoModelForSequenceClassification.from_pretrained(transformer_dir)
            self.model.to(self.device)
            self.model.eval()
            return

        import joblib

        legacy_artifact = resolve_legacy_artifact_file(artifact_path)
        artifact = joblib.load(legacy_artifact)
        self.backend = "legacy"
        self.vectorizer = artifact["vectorizer"]
        self.svd = artifact["svd"]
        self.linear_model = artifact["linear_model"]
        self.rf_model = artifact["rf_model"]
        self.classes = artifact["classes"]

    @staticmethod
    def _apply_keyword_hints(text: str, label: str, confidence: float) -> tuple[str, float]:
        lowered = text.lower()
        for hint_label, keywords in LABEL_HINTS.items():
            matches = sum(1 for keyword in keywords if keyword in lowered)
            if matches >= 2:
                return hint_label, max(confidence, 0.8)
            if matches == 1 and (
                confidence < 0.35
                or (hint_label in MessageClassifier.HIGH_SIGNAL_HINT_LABELS and confidence < 0.55)
            ):
                return hint_label, max(confidence, 0.6)
        return label, confidence

    @staticmethod
    def _softmax(scores):
        import numpy as np

        scores = scores - np.max(scores, axis=1, keepdims=True)
        exp_scores = np.exp(scores)
        return exp_scores / exp_scores.sum(axis=1, keepdims=True)

    def predict(self, text: str) -> dict:
        if self.backend == "transformer":
            import numpy as np

            encoded = self.tokenizer(
                [text],
                truncation=True,
                padding=True,
                max_length=self.max_length,
                return_tensors="pt",
            )
            encoded = {key: value.to(self.device) for key, value in encoded.items()}
            with self.torch.no_grad():
                logits = self.model(**encoded).logits
            probabilities = self.torch.softmax(logits, dim=1)[0].detach().cpu().numpy()
            top_index = int(np.argmax(probabilities))
            label = self.classes[top_index]
            confidence = float(probabilities[top_index])
            label, confidence = self._apply_keyword_hints(text, label, confidence)
            return {
                "label": label,
                "confidence": confidence,
                "risk_indicators": ",".join(self.risk_terms.get(label, ["review"])),
            }

        import numpy as np

        transformed = self.vectorizer.transform([text])
        dense = self.svd.transform(transformed)

        linear_scores = np.clip(self.linear_model.predict(dense), 1e-9, None)
        linear_probs = self._softmax(linear_scores)
        rf_probs = self.rf_model.predict_proba(dense)
        rf_prob_matrix = np.vstack(rf_probs).T if isinstance(rf_probs, list) else rf_probs

        blended = (0.45 * linear_probs) + (0.55 * rf_prob_matrix)
        top_index = int(np.argmax(blended[0]))
        label = self.classes[top_index]
        confidence = float(blended[0][top_index])
        label, confidence = self._apply_keyword_hints(text, label, confidence)

        return {
            "label": label,
            "confidence": confidence,
            "risk_indicators": ",".join(self.risk_terms.get(label, ["review"])),
        }


class HeuristicMessageClassifier:
    PRIORITY_ORDER = [
        "sextortion",
        "grooming",
        "financial_fraud",
        "phishing",
        "malware",
        "violence",
        "hate_speech",
        "sexual_content",
        "cyberbullying",
        "scam",
        "betting",
        "misinformation",
        "bot_activity",
    ]

    def __init__(self):
        self.backend = "heuristic"
        self.risk_terms = RISK_TERMS

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(str(text or "").lower().split())

    def _score_labels(self, text: str) -> list[tuple[str, int]]:
        lowered = self._normalize(text)
        scores: dict[str, int] = {}
        for label, keywords in LABEL_HINTS.items():
            matches = sum(1 for keyword in keywords if keyword in lowered)
            if matches:
                scores[label] = matches

        # A few broad backstops for common message patterns that can cross platforms.
        if any(term in lowered for term in ["http://", "https://", "bit.ly", "tinyurl", "otp", "verify code"]):
            scores["phishing"] = scores.get("phishing", 0) + 1
        if any(term in lowered for term in ["send money", "cashout", "mpesa", "m-pesa", "wallet", "bank alert"]):
            scores["financial_fraud"] = scores.get("financial_fraud", 0) + 1
        if any(term in lowered for term in ["nudes", "video of you", "i will post", "i'll post", "expose you"]):
            scores["sextortion"] = scores.get("sextortion", 0) + 1
        if any(term in lowered for term in ["hate you", "ugly", "fool", "dumb", "useless"]):
            scores["cyberbullying"] = scores.get("cyberbullying", 0) + 1
        if any(term in lowered for term in ["kill", "stab", "beat", "shoot", "die"]):
            scores["violence"] = scores.get("violence", 0) + 1

        ranked = sorted(
            scores.items(),
            key=lambda item: (
                -item[1],
                self.PRIORITY_ORDER.index(item[0]) if item[0] in self.PRIORITY_ORDER else len(self.PRIORITY_ORDER),
                SUPPORTED_LABELS.index(item[0]) if item[0] in SUPPORTED_LABELS else len(SUPPORTED_LABELS),
            ),
        )
        return ranked

    def predict(self, text: str) -> dict:
        ranked = self._score_labels(text)
        if not ranked:
            return {
                "label": SAFE_LABEL,
                "confidence": 0.92,
                "risk_indicators": ",".join(self.risk_terms.get(SAFE_LABEL, ["none"])),
            }

        label, score = ranked[0]
        confidence = min(0.55 + (0.15 * score), 0.9)
        return {
            "label": label,
            "confidence": confidence,
            "risk_indicators": ",".join(self.risk_terms.get(label, ["review"])),
        }


@lru_cache(maxsize=1)
def get_classifier() -> MessageClassifier | HeuristicMessageClassifier | None:
    provider = str(current_app.config.get("MODEL_PROVIDER", "auto")).strip().lower()
    if provider == "heuristic":
        return HeuristicMessageClassifier()

    artifact_path = current_app.config["MODEL_ARTIFACT_PATH"]
    try:
        return MessageClassifier(artifact_path)
    except FileNotFoundError:
        if current_app.config.get("ENABLE_HEURISTIC_FALLBACK", True):
            return HeuristicMessageClassifier()
        return None
