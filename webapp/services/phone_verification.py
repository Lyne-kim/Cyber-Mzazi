from __future__ import annotations

import secrets
from datetime import datetime, timedelta

import requests
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User


def is_sms_configured() -> bool:
    provider = current_app.config.get("SMS_PROVIDER", "africastalking")
    if provider != "africastalking":
        return False
    return bool(
        current_app.config.get("AFRICASTALKING_USERNAME")
        and current_app.config.get("AFRICASTALKING_API_KEY")
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

    ok, message = _send_africastalking_sms(to_phone, body)
    if not ok:
        return False, message

    user.phone_verification_code_hash = generate_password_hash(code)
    user.phone_verification_sent_at = datetime.utcnow()
    db.session.add(user)
    return True, "Phone verification code sent."


def _send_africastalking_sms(to_phone: str, body: str) -> tuple[bool, str]:
    username = current_app.config.get("AFRICASTALKING_USERNAME", "").strip()
    api_key = current_app.config.get("AFRICASTALKING_API_KEY", "")
    sender_id = current_app.config.get("AFRICASTALKING_SENDER_ID", "").strip()
    environment = current_app.config.get("AFRICASTALKING_ENV", "live").strip().lower()
    timeout = int(current_app.config.get("AFRICASTALKING_TIMEOUT", 20))
    if not username or not api_key:
        return False, "Africa's Talking SMS is not configured yet."

    api_base = (
        "https://api.sandbox.africastalking.com"
        if environment == "sandbox"
        else "https://api.africastalking.com"
    )
    payload = {
        "username": username,
        "to": to_phone,
        "message": body,
    }
    if sender_id:
        payload["from"] = sender_id

    try:
        response = requests.post(
            f"{api_base}/version1/messaging",
            data=payload,
            headers={
                "Accept": "application/json",
                "apiKey": api_key,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()
    except requests.RequestException as exc:  # pragma: no cover - network dependent
        return False, f"Phone verification SMS could not be sent: {exc}"
    except ValueError:
        return False, "Phone verification SMS response was not valid JSON."

    recipients = (
        result.get("SMSMessageData", {})
        .get("Recipients", [])
    )
    failed = [
        item for item in recipients
        if str(item.get("status", "")).lower() not in {"success", "sent"}
    ]
    if failed:
        first_failure = failed[0]
        status = first_failure.get("status", "failed")
        error_message = first_failure.get("statusCode", "")
        return False, f"Phone verification SMS failed: {status} {error_message}".strip()

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
