from flask import Blueprint

web_bp = Blueprint(
    "web",
    __name__,
    template_folder="templates",
    static_folder="static",
)


@web_bp.route("/")
def index():
    return "<h1>StockPulse</h1><p>Indian Equity Technical Screener</p>"
