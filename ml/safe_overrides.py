from __future__ import annotations

import re

from .labels import RISK_TERMS, SAFE_LABEL


SAFE_OVERRIDE_CONFIDENCE = 0.99

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
    # Safaricom, M-PESA, and common Safaricom services.
    r"\bsafaricom\b",
    r"\bm[\s._-]?pesa\b",
    r"\bmpesa\b",
    r"\bm[\s._-]?shwari\b",
    r"\bfuliza\b",
    r"\bokoa\b",
    r"\bmy\s*safaricom\b",
    r"\bsafaricom\s*home\b",
    # Kenyan banks and financial institutions.
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
    # TV, fiber, Wi-Fi, and internet providers.
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
    # Shopping and delivery apps/services.
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


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _context_blob(*values: object) -> str:
    raw = " ".join(str(value or "") for value in values if value)
    return _normalize_text(raw.replace("_", " ").replace("-", " ").replace(".", " "))


def _safe_result(reason: str) -> dict:
    return {
        "label": SAFE_LABEL,
        "confidence": SAFE_OVERRIDE_CONFIDENCE,
        "risk_indicators": reason or ",".join(RISK_TERMS[SAFE_LABEL]),
    }


def safe_message_override(
    text: object,
    *,
    source_platform: object = None,
    sender_handle: object = None,
    app_package: object = None,
    notification_title: object = None,
) -> dict | None:
    """Return a safe prediction for known low-risk service notifications."""
    normalized_text = _normalize_text(text)
    if any(normalized_text.startswith(prefix) for prefix in SAFE_SERVICE_PREFIXES):
        return _safe_result("service_callback_message")

    context = _context_blob(source_platform, sender_handle, app_package, notification_title)
    if not context:
        return None

    for pattern in TRUSTED_SOURCE_PATTERNS:
        if re.search(pattern, context):
            return _safe_result("trusted_service_sender")

    return None
