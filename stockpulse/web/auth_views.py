"""Authentication views: login, logout, change password."""

from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from stockpulse.extensions import get_db
from stockpulse.models.user import User

web_auth_bp = Blueprint("web_auth", __name__)


@web_auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("web.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        session = get_db()
        try:
            user = session.query(User).filter(User.email == email).first()

            if user and user.is_active and user.check_password(password):
                user.last_login_at = datetime.now(timezone.utc)
                session.commit()
                login_user(user, remember=request.form.get("remember"))
                next_page = request.args.get("next")
                return redirect(next_page or url_for("web.index"))

            flash("Invalid email or password.", "error")
        finally:
            session.close()

    return render_template("auth/login.html")


@web_auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("web_auth.login"))


@web_auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        confirm_pw = request.form.get("confirm_password", "")

        if not current_user.check_password(current_pw):
            flash("Current password is incorrect.", "error")
        elif len(new_pw) < 8:
            flash("New password must be at least 8 characters.", "error")
        elif new_pw != confirm_pw:
            flash("Passwords do not match.", "error")
        else:
            session = get_db()
            try:
                user = session.query(User).filter(User.id == current_user.id).first()
                user.set_password(new_pw)
                session.commit()
                flash("Password changed successfully.", "success")
                return redirect(url_for("web.index"))
            finally:
                session.close()

    return render_template("auth/change_password.html")
