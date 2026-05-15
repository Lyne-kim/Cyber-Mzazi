from __future__ import annotations

import smtplib
import socket
from email.message import EmailMessage

from flask import current_app


def configured_sender() -> str:
    return (
        current_app.config.get("MAIL_DEFAULT_SENDER", "").strip()
        or current_app.config.get("MAIL_USERNAME", "").strip()
    )


def is_mail_delivery_configured() -> bool:
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

    smtp_class = IPv4SMTP_SSL if use_ssl and force_ipv4 else smtplib.SMTP_SSL if use_ssl else IPv4SMTP if force_ipv4 else smtplib.SMTP

    try:
        smtp = smtp_class(server, port, timeout=20)
        with smtp:
            if use_tls and not use_ssl:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except socket.gaierror:
        return False, "Email server address could not be resolved. Check MAIL_SERVER."
    except TimeoutError:
        return False, "Email server connection timed out. Check MAIL_SERVER and MAIL_PORT."
    except OSError as exc:
        return False, f"Email server connection failed: {exc}"
    except smtplib.SMTPAuthenticationError:
        return False, "Email login failed. Check MAIL_USERNAME and MAIL_PASSWORD."
    except smtplib.SMTPException as exc:
        return False, f"Email delivery failed: {exc}"

    return True, "Email sent."
