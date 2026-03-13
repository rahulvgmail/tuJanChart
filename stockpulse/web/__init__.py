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


# Import sub-blueprints — registered directly on the app (not nested)
# to keep endpoint names short: dashboard.index, web_auth.login, admin.dashboard
from stockpulse.web.auth_views import web_auth_bp  # noqa: F401, E402
from stockpulse.web.admin_views import admin_bp  # noqa: F401, E402
from stockpulse.web.views import dashboard_bp  # noqa: F401, E402
