from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

from .extensions import db, login_manager
from .models import Family, LogoutRequest, User
from .services.audit import log_event


auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    if request.path.startswith("/api/"):
        return {"ok": False, "error": "Authentication required."}, 401
    return redirect(url_for("auth.login"))


@auth_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.role == "parent":
            return redirect(url_for("parent.dashboard"))
        return redirect(url_for("child.dashboard"))
    return redirect(url_for("auth.login"))


def _login_user_by_portal(portal: str, form_data) -> User | None:
    password = form_data.get("password", "")
    if portal == "parent":
        identifier = form_data.get("identifier", "").strip()
        user = User.query.filter(
            User.role == "parent", or_(User.email == identifier, User.phone == identifier)
        ).first()
    else:
        parent_contact = form_data.get("parent_contact", "").strip()
        child_username = form_data.get("child_username", "").strip()
        user = (
            User.query.join(Family)
            .filter(
                User.role == "child",
                User.username == child_username,
                Family.parent_contact == parent_contact,
            )
            .first()
        )
    if not user or not user.check_password(password):
        return None
    return user


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        family_name = request.form.get("family_name", "").strip()
        parent_name = request.form.get("parent_name", "").strip()
        parent_contact = request.form.get("parent_contact", "").strip()
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
        )
        parent_user.set_password(parent_password)

        child_user = User(
            family=family,
            role="child",
            name=child_name,
            username=child_username,
            logout_requires_parent_approval=True,
        )
        child_user.set_password(child_password)

        db.session.add_all([family, parent_user, child_user])
        db.session.flush()
        log_event(family.id, parent_user.id, "family_registered", "Family account created")
        db.session.commit()

        flash("Family account created. Parent can sign in now.", "success")
        return redirect(url_for("auth.parent_login"))

    return render_template("register.html")


@auth_bp.route("/login")
def login():
    return render_template("login.html")


@auth_bp.route("/login/parent", methods=["GET", "POST"])
def parent_login():
    if request.method == "POST":
        user = _login_user_by_portal("parent", request.form)
        if not user:
            flash("Parent login details were not recognised.", "danger")
            return render_template("parent_login.html")

        login_user(user)
        log_event(user.family_id, user.id, "login", f"{user.role} logged in")
        db.session.commit()
        return redirect(url_for("parent.dashboard"))

    return render_template("parent_login.html")


@auth_bp.route("/login/child", methods=["GET", "POST"])
def child_login():
    if request.method == "POST":
        user = _login_user_by_portal("child", request.form)
        if not user:
            flash("Child login details were not recognised.", "danger")
            return render_template("child_login.html")

        login_user(user)
        log_event(user.family_id, user.id, "login", f"{user.role} logged in")
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

    db.session.add(
        LogoutRequest(
            family_id=current_user.family_id,
            child_user_id=current_user.id,
            status="pending",
        )
    )
    log_event(
        current_user.family_id,
        current_user.id,
        "logout_requested",
        "Child requested sign-out approval",
    )
    db.session.commit()
    flash("Parent approval requested.", "info")
    return redirect(url_for("child.dashboard"))


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
    log_event(family_id, actor_id, "logout", f"{role} logged out")
    db.session.commit()
    flash("Signed out successfully.", "success")
    return redirect(url_for("auth.login"))
