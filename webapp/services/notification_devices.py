from __future__ import annotations

import secrets
from datetime import datetime

from ..models import NotificationIngestionDevice


def issue_ingestion_token() -> str:
    return f"cmz_{secrets.token_urlsafe(24)}"


def verify_ingestion_token(token: str) -> NotificationIngestionDevice | None:
    if not token:
        return None
    token_hash = NotificationIngestionDevice.hash_token(token)
    return NotificationIngestionDevice.query.filter_by(
        token_hash=token_hash,
        status="active",
    ).first()


def touch_ingestion_device(
    device: NotificationIngestionDevice,
    *,
    source_platform: str | None = None,
) -> None:
    now = datetime.utcnow()
    device.last_seen_at = now
    device.last_ingested_at = now
    if source_platform:
        device.last_notification_app = source_platform
