from __future__ import annotations

import requests
from flask import current_app


def verify_message(text: str, predicted_label: str) -> dict:
    verifier_url = current_app.config.get("WEB_VERIFIER_URL")
    token = current_app.config.get("WEB_VERIFIER_TOKEN")

    if verifier_url:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = requests.post(
                verifier_url,
                json={"text": text, "predicted_label": predicted_label},
                headers=headers,
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
            return {
                "status": "verified",
                "label": payload.get("label", predicted_label),
                "confidence": float(payload.get("confidence", 0.0)),
                "notes": payload.get("notes", "Verified by external provider."),
            }
        except requests.RequestException as exc:
            return {
                "status": "error",
                "label": predicted_label,
                "confidence": 0.0,
                "notes": f"External verifier failed: {exc}",
            }

    lowered = text.lower()
    heuristics = {
        "betting": ["awin", "instant payout", "odds", "bet", "jackpot", "pesa"],
        "sextortion": ["nudes", "expose", "leak", "send pics", "video yako"],
        "grooming": ["don't tell", "secret", "sleep over", "trust me", "tuko sawa"],
    }
    for label, keywords in heuristics.items():
        if any(keyword in lowered for keyword in keywords):
            return {
                "status": "local_heuristic",
                "label": label,
                "confidence": 0.55,
                "notes": "Matched local fallback heuristic because no verifier is configured.",
            }

    return {
        "status": "not_configured",
        "label": predicted_label,
        "confidence": 0.0,
        "notes": "Configure WEB_VERIFIER_URL to add external confirmation.",
    }
