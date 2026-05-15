from __future__ import annotations

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from .extensions import db, login_manager
from .models import Family, LogoutRequest, User
from .services.audit import log_event
from .services.email_verification import (
    send_verification_email,
    verify_email_token,
)
from .services.parent_alerts import send_logout_request_alert
from .services.phone_verification import (
    normalize_phone,
    send_phone_verification_code,
    verify_phone_code,
)


auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return {"ok": False, "error": "Authentication required."}, 401
    return redirect(url_for("auth.index"))


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.role == "parent":
            return redirect(url_for("parent.dashboard"))
        return redirect(url_for("child.dashboard"))
    return render_template("landing.html")


def _login_user_by_portal(portal: str, form_data) -> User | None:
    password = form_data.get("password", "")
    if portal == "parent":
        identifier = form_data.get("identifier", "").strip()
        normalized_identifier = identifier if "@" in identifier else normalize_phone(identifier)
        user = User.query.filter(
            User.role == "parent",
            or_(User.email == identifier, User.phone == identifier, User.phone == normalized_identifier),
        ).first()
    else:
        raw_parent_contact = form_data.get("parent_contact", "").strip()
        parent_contact = raw_parent_contact if "@" in raw_parent_contact else normalize_phone(raw_parent_contact)
        child_username = form_data.get("child_username", "").strip()
        user = (
            User.query.join(Family)
            .filter(
                User.role == "child",
                User.username == child_username,
                or_(Family.parent_contact == raw_parent_contact, Family.parent_contact == parent_contact),
            )
            .first()
        )
    if not user or not user.check_password(password):
        return None
    return user


def _family_parent_for(user: User) -> User | None:
    return User.query.filter_by(family_id=user.family_id, role="parent").first()


def _verification_message_for(parent_user: User | None) -> str:
    if parent_user is None:
        return "Parent/guardian verification is required before continuing."
    if parent_user.requires_email_verification and not parent_user.email_verified:
        return "Verify the parent email address before signing in."
    if parent_user.requires_phone_verification and not parent_user.phone_verified:
        return "Verify the parent phone number before signing in."
    return "Verify the parent account before signing in."


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        family_name = request.form.get("family_name", "").strip()
        parent_name = request.form.get("parent_name", "").strip()
        parent_contact = request.form.get("parent_contact", "").strip()
        parent_contact = parent_contact if "@" in parent_contact else normalize_phone(parent_contact)
        parent_password = request.form.get("parent_password", "")
        child_name = request.form.get("child_name", "").strip()
        child_username = request.form.get("child_username", "").strip()
        child_password = request.form.get("child_password", "")

        if not all(
            [
                family_name,
                parent_name,
                parent_contact,
                parent_password,
                child_name,
                child_username,
                child_password,
            ]
        ):
            flash("Fill in every registration field.", "warning")
            return render_template("register.html")

        if Family.query.filter_by(parent_contact=parent_contact).first():
            flash("That parent contact is already in use.", "danger")
            return render_template("register.html")
        if User.query.filter_by(username=child_username).first():
            flash("That child username is already in use.", "danger")
            return render_template("register.html")

        family = Family(
            family_name=family_name,
            parent_contact=parent_contact,
            child_display_name=child_name,
        )
        parent_user = User(
            family=family,
            role="parent",
            name=parent_name,
            email=parent_contact if "@" in parent_contact else None,
            phone=parent_contact if "@" not in parent_contact else None,
            logout_requires_parent_approval=False,
            preferred_language="en",
            email_verified=False,
            phone_verified=False,
        )
        parent_user.set_password(parent_password)

        child_user = User(
            family=family,
            role="child",
            name=child_name,
            username=child_username,
            logout_requires_parent_approval=True,
            preferred_language="en",
        )
        child_user.set_password(child_password)

        db.session.add_all([family, parent_user, child_user])
        db.session.flush()
        log_event(
            family.id,
            parent_user.id,
            "family_registered",
            "Family account created",
            subject_user_id=child_user.id,
        )
        verification_message = None
        verification_warning = None
        if parent_user.requires_email_verification:
            ok, message = send_verification_email(parent_user)
            if ok:
                verification_message = message
                log_event(
                    family.id,
                    parent_user.id,
                    "verification_email_sent",
                    f"Verification email sent to {parent_user.email}",
                )
            else:
                verification_warning = message
        if parent_user.requires_phone_verification:
            ok, message = send_phone_verification_code(parent_user)
            if ok:
                verification_message = message
                log_event(
                    family.id,
                    parent_user.id,
                    "phone_verification_sent",
                    f"Phone verification code sent to {parent_user.phone}",
                )
            else:
                verification_warning = message
        db.session.commit()

        if parent_user.requires_email_verification:
            flash(
                "Family account created. Verify the parent email before signing in.",
                "success",
            )
        elif parent_user.requires_phone_verification:
            flash(
                "Family account created. Verify the parent phone number before signing in.",
                "success",
            )
        else:
            flash("Family account created. Parent can sign in now.", "success")
        if verification_warning:
            flash(verification_warning, "warning")
        return redirect(url_for("auth.parent_login"))

    return render_template("register.html")


@auth_bp.route("/login")
def login():
    return redirect(url_for("auth.index"))


@auth_bp.route("/login/parent", methods=["GET", "POST"])
def parent_login():
    if request.method == "POST":
        user = _login_user_by_portal("parent", request.form)
        if not user:
            flash("Invalid parent/guardian email, phone, or password.", "danger")
            return render_template("parent_login.html")
        if not user.can_log_in:
            flash(_verification_message_for(user), "warning")
            return render_template(
                "parent_login.html",
                pending_identifier=user.email or user.phone or "",
            )

        login_user(user)
        log_event(
            user.family_id,
            user.id,
            "login",
            f"{user.role} logged in",
            subject_user_id=user.id if user.role == "child" else None,
        )
        db.session.commit()
        return redirect(url_for("parent.dashboard"))

    return render_template("parent_login.html")


@auth_bp.route("/verify-email/<token>")
def verify_email(token: str):
    user, error = verify_email_token(token)
    if error:
        flash(error, "danger")
        return redirect(url_for("auth.parent_login"))

    if user.email_verified:
        flash("Email address already verified. You can sign in now.", "info")
        return redirect(url_for("auth.parent_login"))

    user.email_verified = True
    user.email_verified_at = datetime.utcnow()
    db.session.add(user)
    log_event(
        user.family_id,
        user.id,
        "email_verified",
        f"Parent email {user.email} verified",
    )
    db.session.commit()
    flash("Email verified successfully. You can sign in now.", "success")
    return redirect(url_for("auth.parent_login"))


@auth_bp.route("/verify-phone", methods=["POST"])
def verify_phone():
    identifier = request.form.get("identifier", "").strip()
    code = request.form.get("code", "").strip()
    normalized_identifier = normalize_phone(identifier)
    user = User.query.filter(
        User.role == "parent",
        or_(User.phone == identifier, User.phone == normalized_identifier),
    ).first()
    if user is None or not user.phone:
        flash("Enter the parent phone number used during registration.", "danger")
        return render_template("parent_login.html", pending_identifier=identifier)

    ok, message = verify_phone_code(user, code)
    if ok:
        log_event(
            user.family_id,
            user.id,
            "phone_verified",
            f"Parent phone {user.phone} verified",
        )
        db.session.commit()
        flash("Phone number verified successfully. You can sign in now.", "success")
        return redirect(url_for("auth.parent_login"))

    db.session.rollback()
    flash(message, "danger")
    return render_template("parent_login.html", pending_identifier=identifier)


@auth_bp.route("/resend-verification", methods=["POST"])
def resend_verification():
    identifier = request.form.get("identifier", "").strip()
    user = User.query.filter(
        User.role == "parent", or_(User.email == identifier, User.phone == identifier)
    ).first()
    if user is None or not user.email:
        flash("Enter the parent email address used during registration.", "danger")
        return render_template("parent_login.html", pending_identifier=identifier)
    if user.email_verified:
        flash("That email is already verified. You can sign in now.", "info")
        return redirect(url_for("auth.parent_login"))

    ok, message = send_verification_email(user)
    if ok:
        log_event(
            user.family_id,
            user.id,
            "verification_email_resent",
            f"Verification email resent to {user.email}",
        )
        db.session.commit()
        flash("Verification email sent again. Check the inbox and spam folder.", "success")
    else:
        db.session.rollback()
        flash(message, "danger")
    return render_template("parent_login.html", pending_identifier=identifier)


@auth_bp.route("/resend-phone-verification", methods=["POST"])
def resend_phone_verification():
    identifier = request.form.get("identifier", "").strip()
    normalized_identifier = normalize_phone(identifier)
    user = User.query.filter(
        User.role == "parent",
        or_(User.phone == identifier, User.phone == normalized_identifier),
    ).first()
    if user is None or not user.phone:
        flash("Enter the parent phone number used during registration.", "danger")
        return render_template("parent_login.html", pending_identifier=identifier)
    if user.phone_verified:
        flash("That phone number is already verified. You can sign in now.", "info")
        return redirect(url_for("auth.parent_login"))

    ok, message = send_phone_verification_code(user)
    if ok:
        log_event(
            user.family_id,
            user.id,
            "phone_verification_resent",
            f"Phone verification code resent to {user.phone}",
        )
        db.session.commit()
        flash("Phone verification code sent again.", "success")
    else:
        db.session.rollback()
        flash(message, "danger")
    return render_template("parent_login.html", pending_identifier=identifier)


@auth_bp.route("/login/child", methods=["GET", "POST"])
def child_login():
    if request.method == "POST":
        user = _login_user_by_portal("child", request.form)
        if not user:
            flash("Invalid child login details. Check the parent/guardian contact, child username, or password.", "danger")
            return render_template("child_login.html")
        parent_user = _family_parent_for(user)
        if parent_user is None or not parent_user.can_log_in:
            flash(_verification_message_for(parent_user), "warning")
            return render_template("child_login.html")

        login_user(user)
        log_event(
            user.family_id,
            user.id,
            "login",
            f"{user.role} logged in",
            subject_user_id=user.id,
        )
        db.session.commit()
        return redirect(url_for("child.dashboard"))

    return render_template("child_login.html")


@auth_bp.route("/request-logout", methods=["POST"])
@login_required
def request_logout():
    if current_user.role != "child":
        flash("Only child accounts use approval-based logout.", "warning")
        return redirect(url_for("parent.dashboard"))

    existing = LogoutRequest.query.filter_by(
        family_id=current_user.family_id, child_user_id=current_user.id, status="pending"
    ).first()
    if existing:
        flash("A logout request is already waiting for parent approval.", "warning")
        return redirect(url_for("child.dashboard"))

    request_note = request.form.get("request_note", "").strip()
    request_details = (
        "Child requested sign-out from this device. "
        "This request ends only the current child session on this device."
    )
    if request_note:
        request_details = f"{request_details} Note from child device: {request_note}"

    logout_request = LogoutRequest(
        family_id=current_user.family_id,
        child_user_id=current_user.id,
        action_type="session_logout",
        action_description=(
            "Child requested sign-out from this device. "
            "This request ends only the current child session on this device."
        ),
        request_note=request_note or None,
        status="pending",
    )
    db.session.add(logout_request)
    log_event(
        current_user.family_id,
        current_user.id,
        "logout_requested",
        request_details,
        subject_user_id=current_user.id,
    )
    parent_user = current_user.family.users.filter_by(role="parent").first()
    email_alert_sent, _email_alert_message = send_logout_request_alert(
        parent_user,
        current_user,
        logout_request,
    )
    if email_alert_sent and parent_user:
        log_event(
            current_user.family_id,
            parent_user.id,
            "parent_alert_emailed",
            f"Parent alert email sent for logout request {logout_request.id}.",
            subject_user_id=current_user.id,
        )
    db.session.commit()
    if email_alert_sent:
        flash("Parent approval requested for sign-out on this device. Parent/guardian email alert sent.", "info")
    else:
        flash("Parent approval requested for sign-out on this device.", "info")
    return redirect(url_for("child.settings"))


@auth_bp.route("/logout")
@login_required
def logout():
    if current_user.role == "child" and current_user.logout_requires_parent_approval:
        approval = (
            LogoutRequest.query.filter_by(
                family_id=current_user.family_id,
                child_user_id=current_user.id,
                status="approved",
            )
            .order_by(LogoutRequest.updated_at.desc())
            .first()
        )
        if not approval:
            flash("Parent approval is required before this child session can sign out.", "danger")
            return redirect(url_for("child.dashboard"))
        approval.status = "used"
        db.session.add(approval)

    family_id = current_user.family_id
    actor_id = current_user.id
    role = current_user.role
    logout_user()
    log_event(
        family_id,
        actor_id,
        "logout",
        f"{role} logged out",
        subject_user_id=actor_id if role == "child" else None,
    )
    db.session.commit()
    flash("Signed out successfully.", "success")
    return redirect(url_for("auth.login"))
