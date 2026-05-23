from __future__ import annotations

import re
from dataclasses import dataclass


GROUP_SUMMARY_PATTERNS = (
    re.compile(r"^\d+\s+new\s+messages?\b", re.IGNORECASE),
    re.compile(r"^\d+\s+messages?\s+from\s+\d+\s+chats?\b", re.IGNORECASE),
    re.compile(r"^new\s+messages?\s+from\s+\d+\s+chats?\b", re.IGNORECASE),
)

SENDER_LINE_PATTERN = re.compile(
    r"^(?P<sender>[A-Za-z0-9 ._@+\-']{2,64}?)(?:[:：]| - | – | — | • )\s*(?P<body>.{2,})$"
)


@dataclass(frozen=True)
class NotificationMessage:
    text: str
    sender_handle: str | None
    notification_title: str | None


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _is_group_summary(text: str) -> bool:
    cleaned = _clean(text)
    return any(pattern.search(cleaned) for pattern in GROUP_SUMMARY_PATTERNS)


def _parse_sender_line(line: str, fallback_sender: str | None) -> tuple[str | None, str]:
    match = SENDER_LINE_PATTERN.match(line)
    if not match:
        return fallback_sender, line

    sender = _clean(match.group("sender"))
    body = _clean(match.group("body"))
    if not body or sender.lower().startswith(("http", "https", "www")):
        return fallback_sender, line
    if sender.lower() in {"new message", "new messages", "message", "messages"}:
        return fallback_sender, body
    return sender, body


def split_notification_messages(
    message_text: str,
    *,
    sender_handle: str | None = None,
    notification_title: str | None = None,
    max_items: int = 80,
) -> list[NotificationMessage]:
    normalized = str(message_text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    raw_lines = [_clean(line) for line in normalized.split("\n")]
    lines = [line for line in raw_lines if len(line) >= 2]
    if len(lines) <= 1:
        if _is_group_summary(normalized):
            return []
        return [NotificationMessage(_clean(normalized), sender_handle, notification_title)]

    messages: list[NotificationMessage] = []
    seen: set[tuple[str | None, str]] = set()
    for line in lines:
        if _is_group_summary(line):
            continue
        parsed_sender, body = _parse_sender_line(line, sender_handle)
        key = (parsed_sender, body)
        if key in seen:
            continue
        seen.add(key)
        messages.append(NotificationMessage(body, parsed_sender, notification_title))
        if len(messages) >= max_items:
            break
    return messages
