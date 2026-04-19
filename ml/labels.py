from __future__ import annotations

from collections import Counter


SAFE_LABEL = "safe"

SUPPORTED_LABELS = [
    SAFE_LABEL,
    "grooming",
    "sexual_content",
    "sextortion",
    "betting",
    "phishing",
    "scam",
    "financial_fraud",
    "malware",
    "cyberbullying",
    "violence",
    "hate_speech",
    "bot_activity",
    "misinformation",
]

RISK_TERMS = {
    SAFE_LABEL: ["none"],
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

LABEL_HINTS = {
    "grooming": ["don't tell", "secret", "trust me", "parents don't understand", "sleep over"],
    "sexual_content": ["sex", "explicit", "nude", "kitandani", "porn"],
    "sextortion": ["send pics", "leak your photos", "expose you", "blackmail", "nudes"],
    "betting": ["odds", "jackpot", "bet", "awin", "payout"],
    "phishing": ["verify your account", "click the link", "password reset", "login now", "account locked"],
    "scam": ["urgent payment", "claim your reward", "true love", "lottery", "bonus portal"],
    "financial_fraud": ["m-pesa pin", "mpesa pin", "send money now", "wire money", "transfer now", "mobile money", "unlock your winnings", "winnings"],
    "malware": ["apk", "macro", "attachment", "payload", "ransomware"],
    "cyberbullying": ["stupid", "worthless", "idiot", "loser", "hate you"],
    "violence": ["kill you", "beat you", "attack you", "hurt you badly", "deserve to die"],
    "hate_speech": ["dirty muslim", "your tribe", "religion is trash", "you people", "slur"],
    "bot_activity": ["automated post", "mass repost", "bot", "fake account", "spam burst"],
    "misinformation": ["fake news", "rumor", "forwards", "hoax", "unverified"],
}

LABEL_METADATA = {
    SAFE_LABEL: {"title": "Safe", "tone": "safe"},
    "grooming": {"title": "Grooming", "tone": "danger"},
    "sexual_content": {"title": "Sexual Content", "tone": "danger"},
    "sextortion": {"title": "Sextortion", "tone": "danger"},
    "betting": {"title": "Betting", "tone": "warning"},
    "phishing": {"title": "Phishing", "tone": "danger"},
    "scam": {"title": "Scam", "tone": "warning"},
    "financial_fraud": {"title": "Financial Fraud", "tone": "danger"},
    "malware": {"title": "Malware", "tone": "danger"},
    "cyberbullying": {"title": "Cyberbullying", "tone": "warning"},
    "violence": {"title": "Violence", "tone": "danger"},
    "hate_speech": {"title": "Hate Speech", "tone": "danger"},
    "bot_activity": {"title": "Bot Activity", "tone": "warning"},
    "misinformation": {"title": "Misinformation", "tone": "warning"},
}


def label_title(label: str) -> str:
    normalized = str(label or "").strip().lower()
    if normalized in LABEL_METADATA:
        return LABEL_METADATA[normalized]["title"]
    return normalized.replace("_", " ").title() or "Unknown"


def label_tone(label: str) -> str:
    normalized = str(label or "").strip().lower()
    return LABEL_METADATA.get(normalized, {}).get("tone", "warning")


def label_summary_rows(labels: list[str]) -> list[dict]:
    counts = Counter(
        label for label in (str(item or "").strip().lower() for item in labels) if label
    )
    rows = []
    for label, count in counts.items():
        rows.append(
            {
                "label": label,
                "title": label_title(label),
                "tone": label_tone(label),
                "count": count,
            }
        )
    rows.sort(
        key=lambda item: (
            -item["count"],
            SUPPORTED_LABELS.index(item["label"])
            if item["label"] in SUPPORTED_LABELS
            else len(SUPPORTED_LABELS),
            item["label"],
        )
    )
    return rows
