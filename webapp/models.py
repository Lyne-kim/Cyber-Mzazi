from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class Family(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    family_name = db.Column(db.String(120), nullable=False)
    parent_contact = db.Column(db.String(120), nullable=False, unique=True)
    child_display_name = db.Column(db.String(120), nullable=False)

    users = db.relationship("User", back_populates="family", lazy="dynamic")
    message_records = db.relationship(
        "MessageRecord", back_populates="family", lazy="dynamic"
    )
    activity_logs = db.relationship(
        "ActivityLog", back_populates="family", lazy="dynamic"
    )
    logout_requests = db.relationship(
        "LogoutRequest", back_populates="family", lazy="dynamic"
    )


class User(UserMixin, TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey("family.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(40))
    username = db.Column(db.String(80))
    password_hash = db.Column(db.String(255), nullable=False)
    logout_requires_parent_approval = db.Column(db.Boolean, default=False, nullable=False)

    family = db.relationship("Family", back_populates="users")
    activity_logs = db.relationship("ActivityLog", back_populates="actor", lazy="dynamic")
    submitted_messages = db.relationship(
        "MessageRecord",
        back_populates="submitted_by",
        lazy="dynamic",
        foreign_keys="MessageRecord.submitted_by_id",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def display_identifier(self) -> str:
        return self.email or self.phone or self.username or self.name


class MessageRecord(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey("family.id"), nullable=False)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    source_platform = db.Column(db.String(60), nullable=False)
    sender_handle = db.Column(db.String(120))
    browser_origin = db.Column(db.String(255))
    message_text = db.Column(db.Text, nullable=False)
    predicted_label = db.Column(db.String(50), nullable=False)
    predicted_confidence = db.Column(db.Float, nullable=False, default=0.0)
    risk_indicators = db.Column(db.Text, nullable=False, default="")
    verification_status = db.Column(db.String(30), nullable=False, default="not_configured")
    verification_label = db.Column(db.String(50))
    verification_confidence = db.Column(db.Float)
    verification_notes = db.Column(db.Text)
    reviewed_label = db.Column(db.String(50))
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    family = db.relationship("Family", back_populates="message_records")
    submitted_by = db.relationship(
        "User",
        back_populates="submitted_messages",
        foreign_keys=[submitted_by_id],
    )


class ActivityLog(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey("family.id"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    event_type = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text, nullable=False, default="")

    family = db.relationship("Family", back_populates="activity_logs")
    actor = db.relationship("User", back_populates="activity_logs")


class LogoutRequest(TimestampMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey("family.id"), nullable=False)
    child_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="pending")
    resolved_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    resolved_at = db.Column(db.DateTime)

    family = db.relationship("Family", back_populates="logout_requests")
    child_user = db.relationship("User", foreign_keys=[child_user_id])
    resolved_by = db.relationship("User", foreign_keys=[resolved_by_id])
