from __future__ import annotations

import re
from urllib.parse import urlparse

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

SAFE_EDUCATIONAL_PHRASES = (
    "education is key",
    "education is the key",
    "education is important",
    "knowledge is power",
    "knowledge gives power",
    "learning is power",
    "learning is important",
    "school is important",
    "study hard",
    "read your books",
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


TRUSTED_LINK_DOMAINS = (
    "safaricom.co.ke",
    "mpesa.in",
    "m-pesa.com",
    "kcbgroup.com",
    "equitygroupholdings.com",
    "equitybankgroup.com",
    "absa.co.ke",
    "ncba.co.ke",
    "co-opbank.co.ke",
    "stanbicbank.co.ke",
    "sc.com",
    "familybank.co.ke",
    "dstv.com",
    "gotvafrica.com",
    "zuku.co.ke",
    "poainternet.net",
    "faiba.co.ke",
    "airtelkenya.com",
    "telkom.co.ke",
    "jumia.co.ke",
    "kilimall.co.ke",
    "kilimall.com",
    "naivas.online",
    "carrefour.ke",
    "glovoapp.com",
    "bolt.eu",
    "uber.com",
    "google.com",
    "youtube.com",
    "whatsapp.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
)

UNSAFE_LINK_CONTEXT_TERMS = (
    "password",
    "otp",
    "pin",
    "verification code",
    "login code",
    "account locked",
    "verify your account",
    "reset your password",
    "send money",
    "urgent payment",
    "claim your reward",
    "private photos",
    "nudes",
)

URL_PATTERN = re.compile(r"(?:https?://|www\.)[^\s<>\"]+", re.IGNORECASE)
PLAIN_DOMAIN_PATTERN = re.compile(r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b", re.IGNORECASE)
HANDLE_ONLY_PATTERN = re.compile(r"^@?[a-z0-9][a-z0-9._-]{1,31}$", re.IGNORECASE)
SOCIAL_CONTEXT_PATTERNS = (
    r"\bwhatsapp\b",
    r"\binstagram\b",
    r"\bfacebook\b",
    r"\bmessenger\b",
    r"\btiktok\b",
    r"\bsnapchat\b",
    r"\btelegram\b",
    r"\btwitter\b",
    r"\bx\b",
    r"\byoutube\b",
    r"\bdiscord\b",
    r"\bthreads\b",
    r"\breddit\b",
    r"\bcom\s+whatsapp\b",
    r"\bcom\s+instagram\b",
    r"\bcom\s+facebook\b",
    r"\bcom\s+messenger\b",
    r"\bcom\s+zhiliaoapp\s+musically\b",
    r"\bcom\s+snapchat\b",
    r"\borg\s+telegram\b",
    r"\bcom\s+twitter\b",
    r"\bcom\s+google\s+android\s+youtube\b",
    r"\bcom\s+discord\b",
)



def split_config_list(raw_value: object) -> tuple[str, ...]:
    raw = str(raw_value or "").replace("\r\n", "\n").replace("\r", "\n")
    parts = re.split(r"[\n;,]+", raw)
    return tuple(part.strip() for part in parts if part.strip())


def _normalize_text(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _context_blob(*values: object) -> str:
    raw = " ".join(str(value or "") for value in values if value)
    return _normalize_text(raw.replace("_", " ").replace("-", " ").replace(".", " "))



def _hostname_from_candidate(candidate: str) -> str:
    candidate = str(candidate or "").strip().rstrip(".,);]")
    if not candidate:
        return ""
    if not candidate.lower().startswith(("http://", "https://")):
        candidate = f"https://{candidate}"
    hostname = urlparse(candidate).hostname or ""
    return hostname.lower().strip(".")


def _is_trusted_domain(hostname: str, domains: tuple[str, ...]) -> bool:
    host = str(hostname or "").lower().strip(".")
    for domain in domains:
        clean_domain = str(domain or "").lower().strip(".")
        if clean_domain and (host == clean_domain or host.endswith(f".{clean_domain}")):
            return True
    return False


def _contains_unsafe_link_context(text: str) -> bool:
    lowered = _normalize_text(text)
    return any(term in lowered for term in UNSAFE_LINK_CONTEXT_TERMS)


def _trusted_link_reason(text: object, extra_domains: tuple[str, ...] = ()) -> str | None:
    normalized_text = str(text or "")
    if _contains_unsafe_link_context(normalized_text):
        return None

    domains = TRUSTED_LINK_DOMAINS + tuple(_normalize_text(domain) for domain in extra_domains)
    candidates = set(URL_PATTERN.findall(normalized_text))
    candidates.update(PLAIN_DOMAIN_PATTERN.findall(normalized_text))
    for candidate in candidates:
        hostname = _hostname_from_candidate(candidate)
        if _is_trusted_domain(hostname, domains):
            return f"trusted_link_domain:{hostname}"
    return None



def _is_social_context(*values: object) -> bool:
    blob = _context_blob(*values)
    return any(re.search(pattern, blob) for pattern in SOCIAL_CONTEXT_PATTERNS)


def _is_handle_only_message(text: object) -> bool:
    value = str(text or "").strip()
    if not value or any(char.isspace() for char in value):
        return False
    if "://" in value or "." in value.strip("@"):  # domains are handled by link policy instead
        return False
    return bool(HANDLE_ONLY_PATTERN.fullmatch(value))

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
    extra_prefixes: tuple[str, ...] = (),
    extra_source_patterns: tuple[str, ...] = (),
    extra_link_domains: tuple[str, ...] = (),
) -> dict | None:
    """Return a safe prediction for known low-risk service notifications."""
    normalized_text = _normalize_text(text)
    if _is_social_context(source_platform, app_package, notification_title, sender_handle) and _is_handle_only_message(text):
        return _safe_result("social_handle_only")

    trusted_link_reason = _trusted_link_reason(text, extra_link_domains)
    if trusted_link_reason:
        return _safe_result(trusted_link_reason)

    if any(phrase and phrase in normalized_text for phrase in SAFE_EDUCATIONAL_PHRASES):
        return _safe_result("safe_educational_phrase")

    safe_prefixes = SAFE_SERVICE_PREFIXES + tuple(_normalize_text(prefix) for prefix in extra_prefixes)
    if any(prefix and normalized_text.startswith(prefix) for prefix in safe_prefixes):
        return _safe_result("service_callback_message")

    context = _context_blob(source_platform, sender_handle, app_package, notification_title)
    if not context:
        return None

    for pattern in TRUSTED_SOURCE_PATTERNS + extra_source_patterns:
        if re.search(pattern, context):
            return _safe_result("trusted_service_sender")

    return None


def safe_override_policy_summary(
    *,
    extra_prefixes: tuple[str, ...] = (),
    extra_source_patterns: tuple[str, ...] = (),
    extra_link_domains: tuple[str, ...] = (),
) -> dict:
    return {
        "default_prefixes": len(SAFE_SERVICE_PREFIXES),
        "default_source_patterns": len(TRUSTED_SOURCE_PATTERNS),
        "default_link_domains": len(TRUSTED_LINK_DOMAINS),
        "extra_prefixes": list(extra_prefixes),
        "extra_source_patterns": list(extra_source_patterns),
        "extra_link_domains": list(extra_link_domains),
    }
