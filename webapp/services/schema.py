from __future__ import annotations

from sqlalchemy import inspect, text

from ..extensions import db


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def ensure_runtime_schema() -> None:
    db.create_all()
    inspector = inspect(db.engine)
    dialect_name = db.engine.dialect.name

    table_names = set(inspector.get_table_names())

    if "user" in table_names and not _column_exists(inspector, "user", "preferred_language"):
        db.session.execute(
            text("ALTER TABLE `user` ADD COLUMN preferred_language VARCHAR(8) DEFAULT 'en'")
        )

    inspector = inspect(db.engine)
    if "user" in table_names and not _column_exists(inspector, "user", "email_verified"):
        db.session.execute(
            text("ALTER TABLE `user` ADD COLUMN email_verified BOOLEAN DEFAULT FALSE")
        )

    inspector = inspect(db.engine)
    if "user" in table_names and not _column_exists(inspector, "user", "email_verified_at"):
        db.session.execute(
            text("ALTER TABLE `user` ADD COLUMN email_verified_at DATETIME NULL")
        )

    inspector = inspect(db.engine)
    if "user" in table_names and not _column_exists(inspector, "user", "verification_email_sent_at"):
        db.session.execute(
            text("ALTER TABLE `user` ADD COLUMN verification_email_sent_at DATETIME NULL")
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

    inspector = inspect(db.engine)
    if "message_record" in table_names and not _column_exists(inspector, "message_record", "source_app_package"):
        db.session.execute(
            text("ALTER TABLE message_record ADD COLUMN source_app_package VARCHAR(255)")
        )

    inspector = inspect(db.engine)
    if "message_record" in table_names and not _column_exists(inspector, "message_record", "notification_title"):
        db.session.execute(
            text("ALTER TABLE message_record ADD COLUMN notification_title VARCHAR(255)")
        )

    inspector = inspect(db.engine)
    if "message_record" in table_names and not _column_exists(inspector, "message_record", "capture_method"):
        db.session.execute(
            text(
                "ALTER TABLE message_record ADD COLUMN capture_method VARCHAR(50) DEFAULT 'manual_report'"
            )
        )

    inspector = inspect(db.engine)
    if "safety_resource_document" in table_names:
        if not _column_exists(inspector, "safety_resource_document", "uploaded_by_id"):
            db.session.execute(
                text("ALTER TABLE safety_resource_document ADD COLUMN uploaded_by_id INTEGER")
            )
        inspector = inspect(db.engine)
        if not _column_exists(inspector, "safety_resource_document", "content_type"):
            db.session.execute(
                text("ALTER TABLE safety_resource_document ADD COLUMN content_type VARCHAR(120)")
            )
        inspector = inspect(db.engine)
        if not _column_exists(inspector, "safety_resource_document", "file_size"):
            db.session.execute(
                text("ALTER TABLE safety_resource_document ADD COLUMN file_size INTEGER DEFAULT 0")
            )
        inspector = inspect(db.engine)
        if not _column_exists(inspector, "safety_resource_document", "binary_data"):
            if dialect_name == "mysql":
                db.session.execute(
                    text("ALTER TABLE safety_resource_document ADD COLUMN binary_data MEDIUMBLOB")
                )
            else:
                db.session.execute(
                    text("ALTER TABLE safety_resource_document ADD COLUMN binary_data BLOB")
                )
        elif dialect_name == "mysql":
            db.session.execute(
                text("ALTER TABLE safety_resource_document MODIFY COLUMN binary_data MEDIUMBLOB NOT NULL")
            )

    db.session.execute(
        text(
            "UPDATE `user` SET preferred_language = 'en' "
            "WHERE preferred_language IS NULL OR preferred_language = ''"
        )
    )
    db.session.execute(
        text(
            "UPDATE `user` SET email_verified = TRUE "
            "WHERE role = 'parent' AND (email IS NULL OR email = '')"
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
    db.session.execute(
        text(
            "UPDATE message_record SET capture_method = 'manual_report' "
            "WHERE capture_method IS NULL OR capture_method = ''"
        )
    )
    if "safety_resource_document" in table_names:
        db.session.execute(
            text(
                "UPDATE safety_resource_document SET file_size = 0 "
                "WHERE file_size IS NULL"
            )
        )
    db.session.commit()
