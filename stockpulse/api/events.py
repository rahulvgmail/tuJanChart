"""Event API endpoints."""

from flask import Blueprint, jsonify, request
from sqlalchemy import desc

from stockpulse.api.auth import get_session, require_api_key
from stockpulse.models.event import Event
from stockpulse.models.stock import Stock

events_bp = Blueprint("api_events", __name__)


@events_bp.route("/events", methods=["GET"])
@require_api_key
def list_events():
    """GET /api/events - List events with optional filters."""
    session = get_session()

    query = session.query(Event).join(Stock, Event.stock_id == Stock.id)

    event_type = request.args.get("event_type")
    if event_type:
        query = query.filter(Event.event_type == event_type)

    symbol = request.args.get("symbol")
    if symbol:
        query = query.filter(
            (Stock.nse_symbol == symbol) | (Stock.symbol == symbol)
        )

    limit = min(int(request.args.get("limit", 50)), 200)

    events = query.order_by(desc(Event.created_at)).limit(limit).all()

    return jsonify({
        "items": [
            {
                "id": e.id,
                "stock_id": e.stock_id,
                "symbol": e.stock.nse_symbol or e.stock.symbol,
                "event_type": e.event_type,
                "payload": e.payload,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
        "total": len(events),
    })


@events_bp.route("/events/<int:event_id>", methods=["GET"])
@require_api_key
def get_event(event_id):
    """GET /api/events/{id} - Event detail."""
    session = get_session()

    event = session.query(Event).filter(Event.id == event_id).first()
    if not event:
        return jsonify({"error": "Event not found"}), 404

    return jsonify({
        "id": event.id,
        "stock_id": event.stock_id,
        "symbol": event.stock.nse_symbol or event.stock.symbol,
        "event_type": event.event_type,
        "payload": event.payload,
        "created_at": event.created_at.isoformat(),
    })
