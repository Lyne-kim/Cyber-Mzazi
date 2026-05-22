from datetime import datetime, timedelta


def resend_wait_seconds(sent_at: datetime | None, cooldown_seconds: int) -> int:
    if sent_at is None or cooldown_seconds <= 0:
        return 0
    available_at = sent_at + timedelta(seconds=cooldown_seconds)
    remaining = (available_at - datetime.utcnow()).total_seconds()
    return max(0, int(remaining + 0.999))
