from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from uuid import uuid4

import requests
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User


def is_sms_configured() -> bool:
    provider = current_app.config.get("SMS_PROVIDER", "textsms")
    if provider != "textsms":
        return False
    return bool(
        current_app.config.get("TEXTSMS_PARTNER_ID")
        and current_app.config.get("TEXTSMS_API_KEY")
        and current_app.config.get("TEXTSMS_SHORTCODE")
    )


def normalize_phone(phone: str) -> str:
    value = "".join(char for char in str(phone or "").strip() if char.isdigit() or char == "+")
    if value.startswith("0") and len(value) == 10:
        return "+254" + value[1:]
    if value.startswith("254"):
        return "+" + value
    return value


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def send_phone_verification_code(user: User) -> tuple[bool, str]:
    if not user.phone:
        return False, "This account does not have a phone number."
    if not is_sms_configured():
        return False, "Phone verification SMS is not configured yet."

    code = _generate_code()
    to_phone = normalize_phone(user.phone)
    max_age = int(current_app.config.get("PHONE_VERIFICATION_CODE_MAX_AGE", 900))
    max_age_minutes = max(1, max_age // 60)
    body = f"Your Cyber Mzazi verification code is {code}. It expires in {max_age_minutes} minutes."

    ok, message = _send_textsms(to_phone, body)
    if not ok:
        return False, message

    user.phone_verification_code_hash = generate_password_hash(code)
    user.phone_verification_sent_at = datetime.utcnow()
    db.session.add(user)
    return True, "Phone verification code sent."


def _send_textsms(to_phone: str, body: str) -> tuple[bool, str]:
    partner_id = current_app.config.get("TEXTSMS_PARTNER_ID", "").strip()
    api_key = current_app.config.get("TEXTSMS_API_KEY", "")
    shortcode = current_app.config.get("TEXTSMS_SHORTCODE", "").strip()
    pass_type = current_app.config.get("TEXTSMS_PASS_TYPE", "plain").strip() or "plain"
    endpoint = current_app.config.get(
        "TEXTSMS_ENDPOINT",
        "https://sms.textsms.co.ke/api/services/sendbulk/",
    ).strip()
    timeout = int(current_app.config.get("TEXTSMS_TIMEOUT", 20))
    if not partner_id or not api_key or not shortcode:
        return False, "TextSMS phone verification is not configured yet."

    client_sms_id = uuid4().hex[:12]
    sms_phone = to_phone[1:] if to_phone.startswith("+") else to_phone
    payload = {
        "count": 1,
        "smslist": [
            {
                "partnerID": partner_id,
                "apikey": api_key,
                "pass_type": pass_type,
                "clientsmsid": client_sms_id,
                "mobile": sms_phone,
                "message": body,
                "shortcode": shortcode,
            }
        ],
    }

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as exc:  # pragma: no cover - network dependent
        return False, f"Phone verification SMS could not be sent: {exc}"
    except ValueError:
        return False, "Phone verification SMS response was not valid JSON."

    responses = result.get("responses", [])
    if not responses:
        return False, "Phone verification SMS response did not include a delivery result."

    first_response = responses[0]
    response_code = str(
        first_response.get("response-code")
        or first_response.get("respose-code")
        or ""
    )
    if response_code != "200":
        description = first_response.get("response-description", "failed")
        return False, f"Phone verification SMS failed: {description} {response_code}".strip()

    return True, "Phone verification code sent."


def verify_phone_code(user: User, code: str) -> tuple[bool, str]:
    if not user.phone:
        return False, "This account does not have a phone number."
    if user.phone_verified:
        return True, "Phone number is already verified."
    if not user.phone_verification_code_hash or not user.phone_verification_sent_at:
        return False, "Request a phone verification code first."

    max_age = int(current_app.config.get("PHONE_VERIFICATION_CODE_MAX_AGE", 900))
    expires_at = user.phone_verification_sent_at + timedelta(seconds=max_age)
    if datetime.utcnow() > expires_at:
        return False, "Phone verification code expired. Request a new code."

    if not check_password_hash(user.phone_verification_code_hash, str(code or "").strip()):
        return False, "Invalid phone verification code."

    user.phone_verified = True
    user.phone_verified_at = datetime.utcnow()
    user.phone_verification_code_hash = None
    db.session.add(user)
    return True, "Phone number verified successfully."
