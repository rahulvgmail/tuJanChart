"""Stock and indicator API endpoints."""

from datetime import date, timedelta

from flask import Blueprint, g, jsonify, request
from sqlalchemy import desc

from stockpulse.api.auth import get_session, require_api_key
from stockpulse.models.annotation import ColorClassification, Note
from stockpulse.models.indicator import StockIndicator
from stockpulse.models.stock import Stock

stocks_bp = Blueprint("api_stocks", __name__)


@stocks_bp.route("/stocks", methods=["GET"])
@require_api_key
def list_stocks():
    """GET /api/stocks - List all stocks with optional filters."""
    session = get_session()

    query = session.query(Stock)

    # Filters
    sector = request.args.get("sector")
    if sector:
        query = query.filter(Stock.sector == sector)

    active = request.args.get("active", "true")
    if active.lower() == "true":
        query = query.filter(Stock.is_active == True)

    stocks = query.order_by(Stock.company_name).all()

    results = []
    for s in stocks:
        # Get current color
        color_row = (
            session.query(ColorClassification.color)
            .filter(
                ColorClassification.stock_id == s.id,
                ColorClassification.is_current == True,
            )
            .first()
        )

        results.append({
            "id": s.id,
            "symbol": s.symbol,
            "nse_symbol": s.nse_symbol,
            "company_name": s.company_name,
            "sector": s.sector,
            "industry": s.industry,
            "is_active": s.is_active,
            "color": color_row.color if color_row else None,
        })

    return jsonify({"items": results, "total": len(results)})


@stocks_bp.route("/stocks/<symbol>", methods=["GET"])
@require_api_key
def get_stock(symbol):
    """GET /api/stocks/{symbol} - Stock detail with latest indicators."""
    session = get_session()

    stock = (
        session.query(Stock)
        .filter((Stock.nse_symbol == symbol) | (Stock.symbol == symbol))
        .first()
    )
    if not stock:
        return jsonify({"error": "Stock not found"}), 404

    # Get latest indicator
    indicator = (
        session.query(StockIndicator)
        .filter(StockIndicator.stock_id == stock.id)
        .order_by(desc(StockIndicator.date))
        .first()
    )

    # Get current color
    color_row = (
        session.query(ColorClassification)
        .filter(
            ColorClassification.stock_id == stock.id,
            ColorClassification.is_current == True,
        )
        .first()
    )

    result = {
        "id": stock.id,
        "symbol": stock.symbol,
        "nse_symbol": stock.nse_symbol,
        "company_name": stock.company_name,
        "sector": stock.sector,
        "industry": stock.industry,
        "is_active": stock.is_active,
        "color": color_row.color if color_row else None,
    }

    if indicator:
        from stockpulse.engine.screener_engine import _indicator_to_dict
        result["indicators"] = _indicator_to_dict(indicator, stock)

    return jsonify(result)


@stocks_bp.route("/stocks/<symbol>/indicators", methods=["GET"])
@require_api_key
def get_indicator_timeseries(symbol):
    """GET /api/stocks/{symbol}/indicators?period=90d - Indicator time-series."""
    session = get_session()

    stock = (
        session.query(Stock)
        .filter((Stock.nse_symbol == symbol) | (Stock.symbol == symbol))
        .first()
    )
    if not stock:
        return jsonify({"error": "Stock not found"}), 404

    # Parse period
    period_str = request.args.get("period", "90d")
    try:
        days = int(period_str.rstrip("d"))
    except ValueError:
        days = 90

    cutoff = date.today() - timedelta(days=days)

    indicators = (
        session.query(StockIndicator)
        .filter(
            StockIndicator.stock_id == stock.id,
            StockIndicator.date >= cutoff,
        )
        .order_by(StockIndicator.date)
        .all()
    )

    series = []
    for ind in indicators:
        series.append({
            "date": ind.date.isoformat(),
            "current_price": float(ind.current_price) if ind.current_price else None,
            "dma_10": float(ind.dma_10) if ind.dma_10 else None,
            "dma_20": float(ind.dma_20) if ind.dma_20 else None,
            "dma_50": float(ind.dma_50) if ind.dma_50 else None,
            "dma_100": float(ind.dma_100) if ind.dma_100 else None,
            "dma_200": float(ind.dma_200) if ind.dma_200 else None,
            "wma_5": float(ind.wma_5) if ind.wma_5 else None,
            "wma_10": float(ind.wma_10) if ind.wma_10 else None,
            "wma_20": float(ind.wma_20) if ind.wma_20 else None,
            "today_volume": ind.today_volume,
            "is_52w_closing_high": ind.is_52w_closing_high,
            "is_volume_breakout": ind.is_volume_breakout,
        })

    return jsonify({
        "symbol": stock.nse_symbol or stock.symbol,
        "company_name": stock.company_name,
        "period_days": days,
        "data_points": len(series),
        "series": series,
    })


@stocks_bp.route("/stocks/<symbol>/notes", methods=["POST"])
@require_api_key
def add_note(symbol):
    """POST /api/stocks/{symbol}/notes - Attach a note to a stock."""
    session = get_session()

    stock = (
        session.query(Stock)
        .filter((Stock.nse_symbol == symbol) | (Stock.symbol == symbol))
        .first()
    )
    if not stock:
        return jsonify({"error": "Stock not found"}), 404

    data = request.get_json()
    if not data or not data.get("content"):
        return jsonify({"error": "content is required"}), 400

    note = Note(
        stock_id=stock.id,
        author_id=g.current_user.id if hasattr(g, "current_user") else None,
        author_type=data.get("author_type", "human"),
        content=data["content"],
    )
    session.add(note)
    session.commit()

    return jsonify({
        "id": note.id,
        "stock_id": note.stock_id,
        "author_type": note.author_type,
        "content": note.content,
        "created_at": note.created_at.isoformat(),
    }), 201


@stocks_bp.route("/stocks/<symbol>/notes", methods=["GET"])
@require_api_key
def list_notes(symbol):
    """GET /api/stocks/{symbol}/notes - List notes for a stock."""
    session = get_session()

    stock = (
        session.query(Stock)
        .filter((Stock.nse_symbol == symbol) | (Stock.symbol == symbol))
        .first()
    )
    if not stock:
        return jsonify({"error": "Stock not found"}), 404

    notes = (
        session.query(Note)
        .filter(Note.stock_id == stock.id)
        .order_by(desc(Note.created_at))
        .all()
    )

    return jsonify({
        "items": [
            {
                "id": n.id,
                "stock_id": n.stock_id,
                "author_id": n.author_id,
                "author_type": n.author_type,
                "content": n.content,
                "created_at": n.created_at.isoformat(),
            }
            for n in notes
        ],
        "total": len(notes),
    })
