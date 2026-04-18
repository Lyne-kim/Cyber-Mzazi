from __future__ import annotations

import smtplib
from datetime import datetime
from email.message import EmailMessage

from flask import current_app, has_request_context, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..extensions import db
from ..models import User

EMAIL_VERIFICATION_SALT = "cyber-mzazi-email-verification"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def is_mail_configured() -> bool:
    return bool(
        current_app.config.get("MAIL_SERVER")
        and current_app.config.get("MAIL_DEFAULT_SENDER")
    )


def generate_email_verification_token(user: User) -> str:
    return _serializer().dumps({"user_id": user.id, "email": user.email}, salt=EMAIL_VERIFICATION_SALT)


def verify_email_token(token: str) -> tuple[User | None, str | None]:
    try:
        payload = _serializer().loads(
            token,
            salt=EMAIL_VERIFICATION_SALT,
            max_age=current_app.config["EMAIL_VERIFICATION_MAX_AGE"],
        )
    except SignatureExpired:
        return None, "Verification link expired."
    except BadSignature:
        return None, "Verification link is invalid."

    user = db.session.get(User, int(payload.get("user_id", 0)))
    if user is None or not user.email:
        return None, "Account was not found."
    if user.email != payload.get("email"):
        return None, "Verification link no longer matches this account."
    return user, None


def build_email_verification_link(user: User) -> str:
    token = generate_email_verification_token(user)
    if has_request_context():
        verification_path = url_for("auth.verify_email", token=token)
    else:
        with current_app.test_request_context():
            verification_path = url_for("auth.verify_email", token=token)
    app_base_url = current_app.config.get("APP_BASE_URL", "")
    if app_base_url:
        return f"{app_base_url}{verification_path}"
    return url_for("auth.verify_email", token=token, _external=True)


def send_verification_email(user: User) -> tuple[bool, str]:
    if not user.email:
        return False, "This account does not have an email address."
    if not is_mail_configured():
        return False, "Email delivery is not configured yet."

    verification_link = build_email_verification_link(user)
    sender = current_app.config["MAIL_DEFAULT_SENDER"]
    message = EmailMessage()
    message["Subject"] = "Verify your Cyber Mzazi email"
    message["From"] = sender
    message["To"] = user.email
    message.set_content(
        (
            f"Hello {user.name},\n\n"
            "Verify your Cyber Mzazi parent account by opening the link below:\n\n"
            f"{verification_link}\n\n"
            "If you did not create this account, you can ignore this email."
        )
    )

    server = current_app.config["MAIL_SERVER"]
    port = current_app.config["MAIL_PORT"]
    username = current_app.config["MAIL_USERNAME"]
    password = current_app.config["MAIL_PASSWORD"]
    use_tls = current_app.config["MAIL_USE_TLS"]
    use_ssl = current_app.config["MAIL_USE_SSL"]

    try:
        if use_ssl:
            smtp: smtplib.SMTP = smtplib.SMTP_SSL(server, port, timeout=20)
        else:
            smtp = smtplib.SMTP(server, port, timeout=20)
        with smtp:
            if use_tls and not use_ssl:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except Exception as exc:  # pragma: no cover - network dependent
        return False, f"Verification email could not be sent: {exc}"

    user.verification_email_sent_at = datetime.utcnow()
    db.session.add(user)
    return True, "Verification email sent."
