from __future__ import annotations

import secrets
from datetime import datetime, timedelta

import requests
from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User


def is_sms_configured() -> bool:
    return bool(
        current_app.config.get("TWILIO_ACCOUNT_SID")
        and current_app.config.get("TWILIO_AUTH_TOKEN")
        and current_app.config.get("TWILIO_FROM_PHONE")
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
    account_sid = current_app.config["TWILIO_ACCOUNT_SID"]
    auth_token = current_app.config["TWILIO_AUTH_TOKEN"]
    from_phone = current_app.config["TWILIO_FROM_PHONE"]
    to_phone = normalize_phone(user.phone)
    max_age = int(current_app.config.get("PHONE_VERIFICATION_CODE_MAX_AGE", 900))
    max_age_minutes = max(1, max_age // 60)
    body = f"Your Cyber Mzazi verification code is {code}. It expires in {max_age_minutes} minutes."

    try:
        response = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
            data={"From": from_phone, "To": to_phone, "Body": body},
            auth=(account_sid, auth_token),
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - network dependent
        return False, f"Phone verification SMS could not be sent: {exc}"

    user.phone_verification_code_hash = generate_password_hash(code)
    user.phone_verification_sent_at = datetime.utcnow()
    db.session.add(user)
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
