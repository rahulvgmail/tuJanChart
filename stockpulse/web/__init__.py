from flask import Blueprint, redirect, url_for
from flask_login import login_required

web_bp = Blueprint(
    "web",
    __name__,
    template_folder="templates",
    static_folder="static",
)


@web_bp.route("/")
@login_required
def index():
    return redirect(url_for("dashboard.index"))


# Register sub-blueprints
from stockpulse.web.auth_views import web_auth_bp
from stockpulse.web.admin_views import admin_bp
from stockpulse.web.views import dashboard_bp

web_bp.register_blueprint(web_auth_bp)
web_bp.register_blueprint(admin_bp)
web_bp.register_blueprint(dashboard_bp)
