from __future__ import annotations

from datetime import datetime
from html import escape

from flask import current_app, has_request_context, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..extensions import db
from ..models import User
from .mail_delivery import is_mail_delivery_configured, send_email

EMAIL_VERIFICATION_SALT = "cyber-mzazi-email-verification"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def is_mail_configured() -> bool:
    return is_mail_delivery_configured()


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
    escaped_link = escape(verification_link, quote=True)
    escaped_name = escape(user.name or "Parent", quote=False)
    plain_body = (
        f"Hello {user.name},\n\n"
        "Verify your Cyber Mzazi parent account before signing in.\n\n"
        f"Click here to verify email: {verification_link}\n\n"
        "If you did not create this account, you can ignore this email."
    )
    html_body = f"""
    <!doctype html>
    <html>
      <body style="margin:0;background:#f6fbff;font-family:Arial,sans-serif;color:#142033;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f6fbff;padding:28px 0;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:18px;padding:30px;border:1px solid #dbe7f3;">
                <tr><td style="font-size:22px;font-weight:700;color:#063b63;">Cyber Mzazi</td></tr>
                <tr><td style="padding-top:18px;font-size:16px;line-height:1.6;">Hello {escaped_name},</td></tr>
                <tr><td style="padding-top:8px;font-size:16px;line-height:1.6;">Please verify your parent account before signing in.</td></tr>
                <tr>
                  <td align="center" style="padding:26px 0;">
                    <a href="{escaped_link}" style="display:inline-block;background:#f5c542;color:#111827;text-decoration:none;font-weight:700;font-size:18px;padding:16px 34px;border-radius:8px;">Verify My Email</a>
                  </td>
                </tr>
                <tr><td style="font-size:14px;line-height:1.6;color:#5f6b7a;">If the button does not work, <a href="{escaped_link}" style="color:#0f766e;font-weight:700;">click here to verify email</a>.</td></tr>
                <tr><td style="padding-top:18px;font-size:13px;color:#7a8797;">If you did not create this account, you can ignore this email.</td></tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    ok, message = send_email(
        user.email,
        "Verify your Cyber Mzazi email",
        plain_body,
        html_body=html_body,
    )
    if not ok:
        return False, f"Verification email could not be sent. {message}"

    user.verification_email_sent_at = datetime.utcnow()
    db.session.add(user)
    return True, "Verification email sent."
