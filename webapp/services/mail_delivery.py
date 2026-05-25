from __future__ import annotations

import smtplib
import socket
from email.message import EmailMessage

from flask import current_app
import requests


def configured_sender() -> str:
    return (
        current_app.config.get("MAIL_DEFAULT_SENDER", "").strip()
        or current_app.config.get("MAIL_USERNAME", "").strip()
    )


def is_mail_delivery_configured() -> bool:
    provider = current_app.config.get("MAIL_PROVIDER", "smtp")
    if provider == "resend":
        return bool(current_app.config.get("RESEND_API_KEY") and configured_sender())
    if provider == "brevo":
        return bool(current_app.config.get("BREVO_API_KEY") and configured_sender())
    return bool(current_app.config.get("MAIL_SERVER") and configured_sender())


def _create_ipv4_connection(host: str, port: int, timeout: int | float | None, source_address=None):
    last_error = None
    for family, socket_type, proto, _canonname, socket_address in socket.getaddrinfo(
        host,
        port,
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
    ):
        sock = None
        try:
            sock = socket.socket(family, socket_type, proto)
            if timeout is not None:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(socket_address)
            return sock
        except OSError as exc:
            last_error = exc
            if sock is not None:
                sock.close()
    if last_error is not None:
        raise last_error
    raise OSError(f"No IPv4 address found for SMTP host {host!r}.")


class IPv4SMTP(smtplib.SMTP):
    def _get_socket(self, host, port, timeout):  # pragma: no cover - network dependent
        return _create_ipv4_connection(host, port, timeout, self.source_address)


class IPv4SMTP_SSL(smtplib.SMTP_SSL):
    def _get_socket(self, host, port, timeout):  # pragma: no cover - network dependent
        sock = _create_ipv4_connection(host, port, timeout, self.source_address)
        return self.context.wrap_socket(sock, server_hostname=self._host)


def send_email(recipient: str, subject: str, body: str) -> tuple[bool, str]:
    if not is_mail_delivery_configured():
        return False, "Email delivery is not configured yet."

    provider = current_app.config.get("MAIL_PROVIDER", "smtp")
    if provider == "resend":
        return _send_email_resend(recipient, subject, body)
    if provider == "brevo":
        return _send_email_brevo(recipient, subject, body)
    if provider != "smtp":
        return False, f"Unsupported MAIL_PROVIDER '{provider}'. Use smtp, resend, or brevo."

    sender = configured_sender()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient
    message.set_content(body)

    server = current_app.config["MAIL_SERVER"]
    port = int(current_app.config["MAIL_PORT"])
    username = current_app.config["MAIL_USERNAME"]
    password = current_app.config["MAIL_PASSWORD"]
    use_tls = current_app.config["MAIL_USE_TLS"]
    use_ssl = current_app.config["MAIL_USE_SSL"]
    force_ipv4 = current_app.config.get("MAIL_FORCE_IPV4", True)
    timeout = max(3, min(int(current_app.config.get("MAIL_TIMEOUT", 10)), 10))
    enable_ssl_fallback = current_app.config.get("MAIL_ENABLE_SSL_FALLBACK", True)
    fallback_ssl_port = int(current_app.config.get("MAIL_FALLBACK_SSL_PORT", 465))

    ok, error = _send_email_with_settings(
        message=message,
        server=server,
        port=port,
        username=username,
        password=password,
        use_tls=use_tls,
        use_ssl=use_ssl,
        force_ipv4=force_ipv4,
        timeout=timeout,
    )
    if ok:
        return True, "Email sent."

    if enable_ssl_fallback and not use_ssl and port != fallback_ssl_port:
        fallback_ok, fallback_error = _send_email_with_settings(
            message=message,
            server=server,
            port=fallback_ssl_port,
            username=username,
            password=password,
            use_tls=False,
            use_ssl=True,
            force_ipv4=force_ipv4,
            timeout=timeout,
        )
        if fallback_ok:
            return True, "Email sent."
        return False, f"{error} Fallback SSL:{fallback_ssl_port} also failed: {fallback_error}"

    return False, error


def _send_email_resend(recipient: str, subject: str, body: str) -> tuple[bool, str]:
    sender = configured_sender()
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {current_app.config['RESEND_API_KEY']}",
                "Content-Type": "application/json",
            },
            json={
                "from": sender,
                "to": [recipient],
                "subject": subject,
                "text": body,
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        return False, f"Email API request failed: {exc}"
    if 200 <= response.status_code < 300:
        return True, "Email sent."
    return False, f"Email API rejected the message: {response.status_code} {response.text[:300]}"


def _send_email_brevo(recipient: str, subject: str, body: str) -> tuple[bool, str]:
    sender = configured_sender()
    sender_name, sender_email = _split_sender(sender)
    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": current_app.config["BREVO_API_KEY"],
                "Content-Type": "application/json",
            },
            json={
                "sender": {"name": sender_name, "email": sender_email},
                "to": [{"email": recipient}],
                "subject": subject,
                "textContent": body,
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        return False, f"Email API request failed: {exc}"
    if 200 <= response.status_code < 300:
        return True, "Email sent."
    return False, f"Email API rejected the message: {response.status_code} {response.text[:300]}"


def _split_sender(sender: str) -> tuple[str, str]:
    if "<" in sender and ">" in sender:
        name = sender.split("<", 1)[0].strip().strip('"') or "Cyber Mzazi"
        email = sender.split("<", 1)[1].split(">", 1)[0].strip()
        return name, email
    return "Cyber Mzazi", sender


def _send_email_with_settings(
    *,
    message: EmailMessage,
    server: str,
    port: int,
    username: str,
    password: str,
    use_tls: bool,
    use_ssl: bool,
    force_ipv4: bool,
    timeout: int,
) -> tuple[bool, str]:
    smtp_class = (
        IPv4SMTP_SSL
        if use_ssl and force_ipv4
        else smtplib.SMTP_SSL
        if use_ssl
        else IPv4SMTP
        if force_ipv4
        else smtplib.SMTP
    )

    try:
        smtp = smtp_class(server, port, timeout=timeout)
        with smtp:
            if use_tls and not use_ssl:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except socket.gaierror:
        return False, "Email server address could not be resolved. Check MAIL_SERVER."
    except TimeoutError:
        return False, f"Email server connection timed out on {server}:{port}."
    except OSError as exc:
        return False, f"Email server connection failed on {server}:{port}: {exc}"
    except smtplib.SMTPAuthenticationError:
        return False, "Email login failed. Check MAIL_USERNAME and MAIL_PASSWORD."
    except smtplib.SMTPException as exc:
        return False, f"Email delivery failed: {exc}"
    except Exception as exc:  # pragma: no cover - defensive guard for provider-specific failures
        current_app.logger.exception("Unexpected email delivery failure.")
        return False, f"Email delivery failed unexpectedly: {exc}"

    return True, "Email sent."
