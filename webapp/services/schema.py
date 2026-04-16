from __future__ import annotations

from sqlalchemy import inspect, text

from ..extensions import db


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def ensure_runtime_schema() -> None:
    db.create_all()
    inspector = inspect(db.engine)

    table_names = set(inspector.get_table_names())

    if "user" in table_names and not _column_exists(inspector, "user", "preferred_language"):
        db.session.execute(
            text("ALTER TABLE `user` ADD COLUMN preferred_language VARCHAR(8) DEFAULT 'en'")
        )

    inspector = inspect(db.engine)
    if "activity_log" in table_names and not _column_exists(inspector, "activity_log", "subject_user_id"):
        db.session.execute(
            text("ALTER TABLE activity_log ADD COLUMN subject_user_id INTEGER")
        )

    inspector = inspect(db.engine)
    if "logout_request" in table_names and not _column_exists(inspector, "logout_request", "action_type"):
        db.session.execute(
            text(
                "ALTER TABLE logout_request ADD COLUMN action_type VARCHAR(50) DEFAULT 'session_logout'"
            )
        )

    inspector = inspect(db.engine)
    if "logout_request" in table_names and not _column_exists(inspector, "logout_request", "action_description"):
        db.session.execute(
            text("ALTER TABLE logout_request ADD COLUMN action_description TEXT")
        )

    inspector = inspect(db.engine)
    if "logout_request" in table_names and not _column_exists(inspector, "logout_request", "request_note"):
        db.session.execute(text("ALTER TABLE logout_request ADD COLUMN request_note TEXT"))

    db.session.execute(
        text(
            "UPDATE `user` SET preferred_language = 'en' "
            "WHERE preferred_language IS NULL OR preferred_language = ''"
        )
    )
    db.session.execute(
        text(
            "UPDATE logout_request SET action_type = 'session_logout' "
            "WHERE action_type IS NULL OR action_type = ''"
        )
    )
    db.session.execute(
        text(
            "UPDATE logout_request "
            "SET action_description = 'Child requested sign-out from this device. "
            "This request ends only the current child session on this device.' "
            "WHERE action_description IS NULL OR action_description = ''"
        )
    )
    db.session.commit()
