"""Stock universe management API endpoints."""

from flask import Blueprint, jsonify, request

from stockpulse.api.auth import get_session, require_api_key
from stockpulse.models.stock import Stock

universe_bp = Blueprint("api_universe", __name__)


@universe_bp.route("/universe", methods=["GET"])
@require_api_key
def list_universe():
    """GET /api/universe - List all stocks with their status."""
    session = get_session()

    stocks = session.query(Stock).order_by(Stock.company_name).all()

    return jsonify({
        "items": [
            {
                "id": s.id,
                "symbol": s.symbol,
                "nse_symbol": s.nse_symbol,
                "company_name": s.company_name,
                "sector": s.sector,
                "is_active": s.is_active,
            }
            for s in stocks
        ],
        "total": len(stocks),
        "active": sum(1 for s in stocks if s.is_active),
    })


@universe_bp.route("/universe", methods=["POST"])
@require_api_key
def add_stock():
    """POST /api/universe - Add a stock to the universe.

    Triggers automatic historical data backfill.
    """
    session = get_session()
    data = request.get_json()

    if not data or not data.get("symbol") or not data.get("company_name"):
        return jsonify({"error": "symbol and company_name are required"}), 400

    # Check if already exists
    existing = session.query(Stock).filter(Stock.symbol == data["symbol"]).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            session.commit()
            return jsonify({
                "id": existing.id,
                "status": "reactivated",
                "symbol": existing.symbol,
            })
        return jsonify({"error": "Stock already exists"}), 409

    stock = Stock(
        symbol=data["symbol"],
        nse_symbol=data.get("nse_symbol"),
        company_name=data["company_name"],
        sector=data.get("sector"),
        industry=data.get("industry"),
        isin=data.get("isin"),
        is_active=True,
    )
    session.add(stock)
    session.commit()

    # Trigger backfill asynchronously
    from stockpulse.ingestion.tasks import backfill_stock
    backfill_stock.delay(stock.id)

    return jsonify({
        "id": stock.id,
        "status": "created",
        "symbol": stock.symbol,
        "nse_symbol": stock.nse_symbol,
        "message": "Historical data backfill started",
    }), 201


@universe_bp.route("/universe/<symbol>", methods=["DELETE"])
@require_api_key
def deactivate_stock(symbol):
    """DELETE /api/universe/{symbol} - Deactivate a stock (data retained)."""
    session = get_session()

    stock = (
        session.query(Stock)
        .filter((Stock.nse_symbol == symbol) | (Stock.symbol == symbol))
        .first()
    )
    if not stock:
        return jsonify({"error": "Stock not found"}), 404

    stock.is_active = False
    session.commit()

    return jsonify({"status": "deactivated", "symbol": symbol})
