from flask import Blueprint

api_bp = Blueprint("api", __name__)


@api_bp.route("/")
def api_index():
    return {"name": "StockPulse API", "version": "0.1.0"}
