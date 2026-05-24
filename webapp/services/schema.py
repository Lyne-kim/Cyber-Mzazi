from __future__ import annotations

from sqlalchemy import inspect, text

from ..extensions import db
from ..models import MessageRecord
from .review_feedback import build_review_signature


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
    if "user" in table_names and not _column_exists(inspector, "user", "phone_verified"):
        db.session.execute(
            text("ALTER TABLE `user` ADD COLUMN phone_verified BOOLEAN DEFAULT FALSE")
        )

    inspector = inspect(db.engine)
    if "user" in table_names and not _column_exists(inspector, "user", "phone_verified_at"):
        db.session.execute(
            text("ALTER TABLE `user` ADD COLUMN phone_verified_at DATETIME NULL")
        )

    inspector = inspect(db.engine)
    if "user" in table_names and not _column_exists(inspector, "user", "phone_verification_code_hash"):
        db.session.execute(
            text("ALTER TABLE `user` ADD COLUMN phone_verification_code_hash VARCHAR(255)")
        )

    inspector = inspect(db.engine)
    if "user" in table_names and not _column_exists(inspector, "user", "phone_verification_sent_at"):
        db.session.execute(
            text("ALTER TABLE `user` ADD COLUMN phone_verification_sent_at DATETIME NULL")
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
    if "message_record" in table_names and not _column_exists(inspector, "message_record", "review_signature"):
        db.session.execute(
            text("ALTER TABLE message_record ADD COLUMN review_signature VARCHAR(512)")
        )

    inspector = inspect(db.engine)
    if "safety_resource_document" in table_names:
        if dialect_name == "mysql":
            db.session.execute(
                text("ALTER TABLE safety_resource_document MODIFY COLUMN family_id INTEGER NULL")
            )
            db.session.execute(
                text("ALTER TABLE safety_resource_document MODIFY COLUMN uploaded_by_id INTEGER NULL")
            )
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
        inspector = inspect(db.engine)
        if not _column_exists(inspector, "safety_resource_document", "title"):
            db.session.execute(text("ALTER TABLE safety_resource_document ADD COLUMN title VARCHAR(180)"))
        inspector = inspect(db.engine)
        if not _column_exists(inspector, "safety_resource_document", "topic"):
            db.session.execute(
                text("ALTER TABLE safety_resource_document ADD COLUMN topic VARCHAR(80) DEFAULT 'Digital safety'")
            )
        inspector = inspect(db.engine)
        if not _column_exists(inspector, "safety_resource_document", "audience"):
            db.session.execute(
                text("ALTER TABLE safety_resource_document ADD COLUMN audience VARCHAR(20) DEFAULT 'all'")
            )
        inspector = inspect(db.engine)
        if not _column_exists(inspector, "safety_resource_document", "summary"):
            db.session.execute(text("ALTER TABLE safety_resource_document ADD COLUMN summary TEXT"))
        inspector = inspect(db.engine)
        if not _column_exists(inspector, "safety_resource_document", "status"):
            db.session.execute(
                text("ALTER TABLE safety_resource_document ADD COLUMN status VARCHAR(30) DEFAULT 'approved'")
            )
        inspector = inspect(db.engine)
        if not _column_exists(inspector, "safety_resource_document", "source_url"):
            db.session.execute(text("ALTER TABLE safety_resource_document ADD COLUMN source_url VARCHAR(500)"))
        inspector = inspect(db.engine)
        if not _column_exists(inspector, "safety_resource_document", "cover_filename"):
            db.session.execute(text("ALTER TABLE safety_resource_document ADD COLUMN cover_filename VARCHAR(255)"))
        inspector = inspect(db.engine)
        if not _column_exists(inspector, "safety_resource_document", "cover_content_type"):
            db.session.execute(text("ALTER TABLE safety_resource_document ADD COLUMN cover_content_type VARCHAR(120)"))
        inspector = inspect(db.engine)
        if not _column_exists(inspector, "safety_resource_document", "cover_binary_data"):
            if dialect_name == "mysql":
                db.session.execute(
                    text("ALTER TABLE safety_resource_document ADD COLUMN cover_binary_data MEDIUMBLOB")
                )
            else:
                db.session.execute(
                    text("ALTER TABLE safety_resource_document ADD COLUMN cover_binary_data BLOB")
                )

    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "safety_resource_link" in table_names:
        if dialect_name == "mysql":
            db.session.execute(
                text("ALTER TABLE safety_resource_link MODIFY COLUMN family_id INTEGER NULL")
            )
            db.session.execute(
                text("ALTER TABLE safety_resource_link MODIFY COLUMN created_by_id INTEGER NULL")
            )
        if not _column_exists(inspector, "safety_resource_link", "status"):
            db.session.execute(
                text("ALTER TABLE safety_resource_link ADD COLUMN status VARCHAR(30) DEFAULT 'approved'")
            )

    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "deleted_message_signature" not in table_names:
        if dialect_name == "mysql":
            db.session.execute(
                text(
                    "CREATE TABLE deleted_message_signature ("
                    "id INTEGER NOT NULL AUTO_INCREMENT, "
                    "family_id INTEGER NOT NULL, "
                    "child_user_id INTEGER NOT NULL, "
                    "deleted_by_id INTEGER NULL, "
                    "review_signature VARCHAR(512) NOT NULL, "
                    "source_platform VARCHAR(60) NULL, "
                    "source_app_package VARCHAR(255) NULL, "
                    "sender_handle VARCHAR(120) NULL, "
                    "notification_title VARCHAR(255) NULL, "
                    "message_excerpt TEXT NULL, "
                    "created_at DATETIME NOT NULL, "
                    "updated_at DATETIME NOT NULL, "
                    "PRIMARY KEY (id), "
                    "INDEX ix_deleted_message_signature_review_signature (review_signature)"
                    ")"
                )
            )
        else:
            db.session.execute(
                text(
                    "CREATE TABLE deleted_message_signature ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "family_id INTEGER NOT NULL, "
                    "child_user_id INTEGER NOT NULL, "
                    "deleted_by_id INTEGER, "
                    "review_signature VARCHAR(512) NOT NULL, "
                    "source_platform VARCHAR(60), "
                    "source_app_package VARCHAR(255), "
                    "sender_handle VARCHAR(120), "
                    "notification_title VARCHAR(255), "
                    "message_excerpt TEXT, "
                    "created_at DATETIME NOT NULL, "
                    "updated_at DATETIME NOT NULL"
                    ")"
                )
            )
            db.session.execute(
                text(
                    "CREATE INDEX ix_deleted_message_signature_review_signature "
                    "ON deleted_message_signature (review_signature)"
                )
            )

    db.session.execute(
        text(
            "UPDATE `user` SET preferred_language = 'en' "
            "WHERE preferred_language IS NULL OR preferred_language = ''"
        )
    )
    db.session.execute(
        text(
            "UPDATE `user` SET email_verified = FALSE "
            "WHERE role = 'parent' AND email IS NOT NULL AND email != '' AND email_verified IS NULL"
        )
    )
    db.session.execute(
        text(
            "UPDATE `user` SET phone_verified = FALSE "
            "WHERE role = 'parent' AND phone IS NOT NULL AND phone != '' AND phone_verified IS NULL"
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
        db.session.execute(
            text(
                "UPDATE safety_resource_document SET title = filename "
                "WHERE title IS NULL OR title = ''"
            )
        )
        db.session.execute(
            text(
                "UPDATE safety_resource_document SET topic = 'Digital safety' "
                "WHERE topic IS NULL OR topic = ''"
            )
        )
        db.session.execute(
            text(
                "UPDATE safety_resource_document SET audience = 'all' "
                "WHERE audience IS NULL OR audience = ''"
            )
        )
        db.session.execute(
            text(
                "UPDATE safety_resource_document SET status = 'approved' "
                "WHERE status IS NULL OR status = ''"
            )
        )
    if "safety_resource_link" in table_names:
        db.session.execute(
            text(
                "UPDATE safety_resource_link SET status = 'approved' "
                "WHERE status IS NULL OR status = ''"
            )
        )
    if "message_record" in table_names:
        for record in MessageRecord.query.filter(
            (MessageRecord.review_signature.is_(None)) | (MessageRecord.review_signature == "")
        ).all():
            record.review_signature = build_review_signature(record.message_text)
    db.session.commit()
