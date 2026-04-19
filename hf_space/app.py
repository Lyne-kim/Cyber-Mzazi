from __future__ import annotations

import json
import os
import shutil
import tempfile
from functools import lru_cache
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse
from zipfile import ZipFile

import numpy as np
import requests
import torch
from flask import Flask, jsonify, request
from transformers import AutoModelForSequenceClassification, AutoTokenizer


DEFAULT_MODEL_ARTIFACT_URL = (
    "https://github.com/Lyne-kim/Cyber-Mzazi/releases/download/model-stage3/"
    "message_model_stage3.zip"
)
ARTIFACT_DIR = Path(os.getenv("MODEL_ARTIFACT_PATH", "/tmp/message_model_stage3"))
MODEL_ARTIFACT_URL = os.getenv("MODEL_ARTIFACT_URL", DEFAULT_MODEL_ARTIFACT_URL).strip()
MODEL_INFERENCE_TOKEN = os.getenv("MODEL_INFERENCE_TOKEN", "").strip()

LABEL_HINTS = {
    "grooming": ["don't tell", "secret", "trust me", "parents don't understand", "sleep over"],
    "sexual_content": ["sex", "explicit", "nude", "kitandani", "porn"],
    "sextortion": ["send pics", "leak your photos", "expose you", "blackmail", "nudes"],
    "betting": ["odds", "jackpot", "bet", "awin", "payout"],
    "phishing": ["verify your account", "click the link", "password reset", "login now", "account locked"],
    "scam": ["urgent payment", "claim your reward", "true love", "lottery", "bonus portal"],
    "financial_fraud": ["m-pesa pin", "mpesa pin", "send money now", "wire money", "transfer now", "mobile money"],
    "malware": ["apk", "macro", "attachment", "payload", "ransomware"],
    "cyberbullying": ["stupid", "worthless", "idiot", "loser", "hate you"],
    "violence": ["kill you", "beat you", "attack you", "hurt you badly", "deserve to die"],
    "hate_speech": ["dirty muslim", "your tribe", "religion is trash", "you people", "slur"],
    "bot_activity": ["automated post", "mass repost", "bot", "fake account", "spam burst"],
    "misinformation": ["fake news", "rumor", "forwards", "hoax", "unverified"],
}

RISK_TERMS = {
    "safe": ["none"],
    "grooming": ["trust_building", "secrecy", "isolation"],
    "sexual_content": ["sexual_language", "explicit_content", "boundary_risk"],
    "sextortion": ["coercion", "blackmail", "image_threat"],
    "betting": ["gambling", "financial_pressure", "false_promises"],
    "phishing": ["credential_theft", "fake_link", "impersonation"],
    "scam": ["social_engineering", "financial_request", "fraud"],
    "financial_fraud": ["money_transfer", "urgent_payment", "account_takeover"],
    "malware": ["malicious_attachment", "payload_delivery", "device_compromise"],
    "cyberbullying": ["harassment", "abuse", "threat_language"],
    "violence": ["physical_harm", "attack_language", "death_threat"],
    "hate_speech": ["identity_attack", "religious_abuse", "targeted_slur"],
    "bot_activity": ["automation", "spam_pattern", "fake_account"],
    "misinformation": ["false_claims", "manipulation", "deception"],
}

_load_lock = Lock()


def transformer_artifact_exists(path: Path) -> bool:
    return path.is_dir() and (path / "config.json").exists() and (path / "metadata.json").exists()


def download_and_extract_transformer_artifact(artifact_url: str, artifact_dir: Path) -> Path:
    artifact_dir.parent.mkdir(parents=True, exist_ok=True)
    temp_root = artifact_dir.parent / ".model_download_tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    archive_name = Path(urlparse(artifact_url).path).name or "message_model.zip"

    try:
        with tempfile.TemporaryDirectory(prefix="cyber-mzazi-model-", dir=temp_root) as tmp_dir:
            archive_path = Path(tmp_dir) / archive_name
            with requests.get(artifact_url, stream=True, timeout=900) as response:
                response.raise_for_status()
                with archive_path.open("wb") as file_handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            file_handle.write(chunk)

            extracted_dir = Path(tmp_dir) / "extracted"
            extracted_dir.mkdir(parents=True, exist_ok=True)
            with ZipFile(archive_path) as archive:
                archive.extractall(extracted_dir)

            config_files = list(extracted_dir.rglob("config.json"))
            if not config_files:
                raise RuntimeError("Downloaded archive did not contain a transformer artifact.")

            source_dir = config_files[0].parent
            if artifact_dir.exists():
                shutil.rmtree(artifact_dir)
            shutil.copytree(source_dir, artifact_dir)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    return artifact_dir


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

    def __init__(self, artifact_dir: Path):
        metadata = json.loads((artifact_dir / "metadata.json").read_text(encoding="utf-8"))
        self.max_length = int(metadata.get("max_length", 160))
        self.classes = metadata["classes"]
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(artifact_dir, use_fast=False)
        self.model = AutoModelForSequenceClassification.from_pretrained(artifact_dir)
        self.model.to(self.device)
        self.model.eval()

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

    def predict(self, text: str) -> dict:
        encoded = self.tokenizer(
            [text],
            truncation=True,
            padding=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self.device) for key, value in encoded.items()}
        with torch.no_grad():
            logits = self.model(**encoded).logits
        probabilities = torch.softmax(logits, dim=1)[0].detach().cpu().numpy()
        top_index = int(np.argmax(probabilities))
        label = self.classes[top_index]
        confidence = float(probabilities[top_index])
        label, confidence = self._apply_keyword_hints(text, label, confidence)
        return {
            "label": label,
            "confidence": confidence,
            "risk_indicators": ",".join(RISK_TERMS.get(label, ["review"])),
        }


@lru_cache(maxsize=1)
def get_classifier() -> MessageClassifier:
    with _load_lock:
        if not transformer_artifact_exists(ARTIFACT_DIR):
            download_and_extract_transformer_artifact(MODEL_ARTIFACT_URL, ARTIFACT_DIR)
        return MessageClassifier(ARTIFACT_DIR)


app = Flask(__name__)


def is_authorized() -> bool:
    if not MODEL_INFERENCE_TOKEN:
        return True
    auth_header = request.headers.get("Authorization", "").strip()
    return auth_header.lower().startswith("bearer ") and auth_header[7:].strip() == MODEL_INFERENCE_TOKEN


@app.get("/")
def index():
    return jsonify(
        {
            "ok": True,
            "service": "cyber-mzazi-hf-space",
            "endpoints": ["/health", "/predict"],
        }
    )


@app.get("/health")
def health():
    ready = transformer_artifact_exists(ARTIFACT_DIR)
    return jsonify(
        {
            "ok": True,
            "service": "cyber-mzazi-hf-space",
            "artifact_ready": ready,
            "artifact_path": str(ARTIFACT_DIR),
        }
    )


@app.post("/predict")
def predict():
    if not is_authorized():
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", "")).strip()
    if not text:
        return jsonify({"ok": False, "error": "Text is required."}), 400

    try:
        classifier = get_classifier()
        prediction = classifier.predict(text)
        return jsonify({"ok": True, "prediction": prediction})
    except Exception as exc:  # pragma: no cover - deployment safety
        return jsonify({"ok": False, "error": f"Prediction failed: {exc}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
