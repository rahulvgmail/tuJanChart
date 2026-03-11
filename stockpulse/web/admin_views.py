"""Admin views: user management, API key management, system health."""

import secrets
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from stockpulse.extensions import get_db
from stockpulse.models.user import APIKey, User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Decorator that requires the current user to be an admin."""

    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("Admin access required.", "error")
            return redirect(url_for("web.index"))
        return f(*args, **kwargs)

    return decorated


@admin_bp.route("/")
@admin_required
def dashboard():
    session = get_db()
    try:
        users = session.query(User).order_by(User.email).all()
        api_keys = (
            session.query(APIKey)
            .join(User)
            .order_by(APIKey.created_at.desc())
            .all()
        )
        return render_template("admin/dashboard.html", users=users, api_keys=api_keys)
    finally:
        session.close()


@admin_bp.route("/users/invite", methods=["POST"])
@admin_required
def invite_user():
    email = request.form.get("email", "").strip()
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "member")

    if not email:
        flash("Email is required.", "error")
        return redirect(url_for("admin.dashboard"))

    if role not in ("member", "admin"):
        role = "member"

    session = get_db()
    try:
        existing = session.query(User).filter(User.email == email).first()
        if existing:
            flash(f"User {email} already exists.", "error")
            return redirect(url_for("admin.dashboard"))

        # Generate a temporary password
        temp_password = secrets.token_urlsafe(12)
        user = User(email=email, name=name or None, role=role)
        user.set_password(temp_password)
        session.add(user)
        session.commit()

        flash(
            f"User {email} created. Temporary password: {temp_password} — "
            "share securely and ask them to change it.",
            "success",
        )
    finally:
        session.close()

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id):
    if user_id == current_user.id:
        flash("You cannot deactivate yourself.", "error")
        return redirect(url_for("admin.dashboard"))

    session = get_db()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            flash("User not found.", "error")
        else:
            user.is_active = not user.is_active
            session.commit()
            status = "activated" if user.is_active else "deactivated"
            flash(f"User {user.email} {status}.", "success")
    finally:
        session.close()

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/api-keys/create", methods=["POST"])
@admin_required
def create_api_key():
    user_id = request.form.get("user_id", type=int)
    label = request.form.get("label", "").strip()

    if not user_id:
        flash("User is required.", "error")
        return redirect(url_for("admin.dashboard"))

    session = get_db()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            flash("User not found.", "error")
            return redirect(url_for("admin.dashboard"))

        raw_key = f"sp_{secrets.token_urlsafe(32)}"
        api_key = APIKey(
            user_id=user.id,
            key_hash=APIKey.hash_key(raw_key),
            label=label or None,
        )
        session.add(api_key)
        session.commit()

        flash(
            f"API key created for {user.email}: {raw_key} — "
            "copy now, it won't be shown again.",
            "success",
        )
    finally:
        session.close()

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/api-keys/<int:key_id>/revoke", methods=["POST"])
@admin_required
def revoke_api_key(key_id):
    session = get_db()
    try:
        api_key = session.query(APIKey).filter(APIKey.id == key_id).first()
        if not api_key:
            flash("API key not found.", "error")
        else:
            api_key.is_active = False
            session.commit()
            flash("API key revoked.", "success")
    finally:
        session.close()

    return redirect(url_for("admin.dashboard"))
