from __future__ import annotations

import json
import os
import re
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
SAFE_MESSAGE_PREFIXES = os.getenv("SAFE_MESSAGE_PREFIXES", "").strip()
SAFE_SENDER_PATTERNS = os.getenv("SAFE_SENDER_PATTERNS", "").strip()

LABEL_HINTS = {
    "grooming": ["don't tell", "secret", "trust me", "parents don't understand", "sleep over"],
    "sexual_content": ["sex", "explicit", "nude", "kitandani", "porn"],
    "sextortion": ["send pics", "leak your photos", "expose you", "blackmail", "nudes"],
    "betting": ["odds", "jackpot", "bet", "awin", "payout"],
    "phishing": ["verify your account", "click the link", "password reset", "login now", "account locked"],
    "scam": ["urgent payment", "claim your reward", "true love", "lottery", "bonus portal", "m-pesa pin", "mpesa pin", "send money now", "wire money", "transfer now", "mobile money"],
    "cyberbullying": ["stupid", "worthless", "idiot", "loser", "hate you"],
    "violence": ["kill you", "beat you", "attack you", "hurt you badly", "deserve to die"],
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
    "cyberbullying": ["harassment", "abuse", "threat_language"],
    "violence": ["physical_harm", "attack_language", "death_threat"],
    "misinformation": ["false_claims", "manipulation", "deception"],
}

SUPPORTED_LABELS = set(RISK_TERMS)
LABEL_ALIASES = {
    "malware": "phishing",
    "defacement": "phishing",
    "bot_activity": "scam",
    "bot": "scam",
    "toxic": "cyberbullying",
    "hate": "cyberbullying",
    "sexual": "sexual_content",
    "fake": "misinformation",
}

SAFE_SERVICE_PREFIXES = (
    "i tried to call at",
    "i tried calling at",
    "i tried to call you at",
    "please call me",
    "please call me back",
    "pls call me",
    "call me back",
    "you have a missed call",
    "missed call from",
    "nilijaribu kukupigia",
    "nimejaribu kukupigia",
    "tafadhali nipigie",
)

TRUSTED_SOURCE_PATTERNS = (
    r"\bsafaricom\b",
    r"\bm[\s._-]?pesa\b",
    r"\bmpesa\b",
    r"\bm[\s._-]?shwari\b",
    r"\bfuliza\b",
    r"\bokoa\b",
    r"\bmy\s*safaricom\b",
    r"\bsafaricom\s*home\b",
    r"\bbank\b",
    r"\bbanking\b",
    r"\bkcb\b",
    r"\bequity\b",
    r"\bequitel\b",
    r"\babsa\b",
    r"\bncba\b",
    r"\bcoop\b",
    r"\bco[\s._-]?op\b",
    r"\bco[\s._-]?operative\b",
    r"\bstanbic\b",
    r"\bstanchart\b",
    r"\bstandard\s*chartered\b",
    r"\bdtb\b",
    r"\bi\s*&\s*m\b",
    r"\bfamily\s*bank\b",
    r"\bnational\s*bank\b",
    r"\bkingdom\s*bank\b",
    r"\bsidian\b",
    r"\bcredit\s*bank\b",
    r"\bprime\s*bank\b",
    r"\buba\b",
    r"\bboa\b",
    r"\bstima\s*sacco\b",
    r"\bmwalimu\s*sacco\b",
    r"\bdstv\w*\b",
    r"\bdstv[\s._-]?kenya\b",
    r"\bgotv\w*\b",
    r"\bzuku\b",
    r"\bstar[\s._-]?times\b",
    r"\bpoa\s*internet\b",
    r"\bfaiba\b",
    r"\bjamii\s*telecom\b",
    r"\bjtl\b",
    r"\bliquid\s*(home|telecom)?\b",
    r"\btelkom\b",
    r"\bairtel\b",
    r"\bjumia\b",
    r"\bkilimall\b",
    r"\baliexpress\b",
    r"\bshein\b",
    r"\btemu\b",
    r"\bnaivas\b",
    r"\bcarrefour\b",
    r"\bglovo\b",
    r"\bbolt\s*food\b",
    r"\buber\s*eats\b",
    r"\blittle\s*cab\b",
    r"\bbolt\b",
)


def normalize_label(label: str | None) -> str:
    normalized = str(label or "").strip().lower()
    normalized = LABEL_ALIASES.get(normalized, normalized)
    return normalized if normalized in SUPPORTED_LABELS else "safe"


def normalize_text(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def split_config_list(raw_value: object) -> tuple[str, ...]:
    raw = str(raw_value or "").replace("\r\n", "\n").replace("\r", "\n")
    parts = re.split(r"[\n;,]+", raw)
    return tuple(part.strip() for part in parts if part.strip())


def safe_message_override(
    text: object,
    *,
    source_platform: object = None,
    sender_handle: object = None,
    app_package: object = None,
    notification_title: object = None,
) -> dict | None:
    normalized_text = normalize_text(text)
    safe_prefixes = SAFE_SERVICE_PREFIXES + tuple(
        normalize_text(prefix) for prefix in split_config_list(SAFE_MESSAGE_PREFIXES)
    )
    if any(prefix and normalized_text.startswith(prefix) for prefix in safe_prefixes):
        return {"label": "safe", "confidence": 0.99, "risk_indicators": "service_callback_message"}

    context = " ".join(
        str(value or "")
        for value in (source_platform, sender_handle, app_package, notification_title)
        if value
    )
    context = normalize_text(context.replace("_", " ").replace("-", " ").replace(".", " "))
    if not context:
        return None

    for pattern in TRUSTED_SOURCE_PATTERNS + split_config_list(SAFE_SENDER_PATTERNS):
        if re.search(pattern, context):
            return {"label": "safe", "confidence": 0.99, "risk_indicators": "trusted_service_sender"}

    return None

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
        "grooming",
        "sextortion",
        "violence",
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
        label = normalize_label(self.classes[top_index])
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

    safe_override = safe_message_override(
        text,
        source_platform=payload.get("source_platform") or payload.get("app_name"),
        sender_handle=payload.get("sender_handle"),
        app_package=payload.get("app_package"),
        notification_title=payload.get("notification_title"),
    )
    if safe_override is not None:
        return jsonify({"ok": True, "prediction": safe_override})

    try:
        classifier = get_classifier()
        prediction = classifier.predict(text)
        return jsonify({"ok": True, "prediction": prediction})
    except Exception as exc:  # pragma: no cover - deployment safety
        return jsonify({"ok": False, "error": f"Prediction failed: {exc}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "7860")))
