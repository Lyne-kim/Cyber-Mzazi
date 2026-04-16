from ..extensions import db
from ..models import ActivityLog


def log_event(
    family_id: int,
    actor_id: int | None,
    event_type: str,
    details: str,
    *,
    subject_user_id: int | None = None,
) -> None:
    log = ActivityLog(
        family_id=family_id,
        actor_id=actor_id,
        subject_user_id=subject_user_id,
        event_type=event_type,
        details=details,
    )
    db.session.add(log)
