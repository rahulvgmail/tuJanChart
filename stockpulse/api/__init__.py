from flask import Blueprint

api_bp = Blueprint("api", __name__)


@api_bp.route("/")
def api_index():
    return {"name": "StockPulse API", "version": "0.1.0"}


# Register sub-blueprints
from stockpulse.api.stocks import stocks_bp
from stockpulse.api.screeners import screeners_bp
from stockpulse.api.events import events_bp
from stockpulse.api.webhooks import webhooks_bp
from stockpulse.api.universe import universe_bp

api_bp.register_blueprint(stocks_bp)
api_bp.register_blueprint(screeners_bp)
api_bp.register_blueprint(events_bp)
api_bp.register_blueprint(webhooks_bp)
api_bp.register_blueprint(universe_bp)
