"""Screener API endpoints."""

from datetime import date

from flask import Blueprint, g, jsonify, request
from sqlalchemy import desc

from stockpulse.api.auth import get_session, require_api_key
from stockpulse.engine.screener_engine import ScreenerEngine
from stockpulse.models.screener import Screener, ScreenerCondition

screeners_bp = Blueprint("api_screeners", __name__)


@screeners_bp.route("/screeners", methods=["GET"])
@require_api_key
def list_screeners():
    """GET /api/screeners - List all screeners."""
    session = get_session()

    screeners = (
        session.query(Screener)
        .filter(Screener.is_active == True)
        .order_by(Screener.category, Screener.name)
        .all()
    )

    results = []
    for s in screeners:
        cond_count = (
            session.query(ScreenerCondition)
            .filter(ScreenerCondition.screener_id == s.id)
            .count()
        )
        results.append({
            "id": s.id,
            "name": s.name,
            "slug": s.slug,
            "category": s.category,
            "is_builtin": s.is_builtin,
            "is_active": s.is_active,
            "condition_count": cond_count,
        })

    return jsonify({"items": results, "total": len(results)})


@screeners_bp.route("/screeners/<int:screener_id>/results", methods=["GET"])
@require_api_key
def get_screener_results(screener_id):
    """GET /api/screeners/{id}/results - Run screener and return matching stocks."""
    session = get_session()

    screener = session.query(Screener).filter(Screener.id == screener_id).first()
    if not screener:
        return jsonify({"error": "Screener not found"}), 404

    # Parse optional filters
    extra_filters = {}
    if request.args.get("min_pe"):
        extra_filters["min_pe"] = float(request.args["min_pe"])
    if request.args.get("max_pe"):
        extra_filters["max_pe"] = float(request.args["max_pe"])
    if request.args.get("min_mcap"):
        extra_filters["min_mcap"] = float(request.args["min_mcap"])
    if request.args.get("max_mcap"):
        extra_filters["max_mcap"] = float(request.args["max_mcap"])
    if request.args.get("color"):
        extra_filters["color"] = request.args.getlist("color")
    if request.args.get("sector"):
        extra_filters["sector"] = request.args["sector"]

    as_of_str = request.args.get("date")
    as_of = date.fromisoformat(as_of_str) if as_of_str else None

    engine = ScreenerEngine(session)
    results = engine.evaluate(
        screener_id, as_of=as_of, extra_filters=extra_filters or None
    )

    return jsonify({
        "screener": {
            "id": screener.id,
            "name": screener.name,
            "slug": screener.slug,
        },
        "date": as_of.isoformat() if as_of else None,
        "total": len(results),
        "items": results,
    })


@screeners_bp.route("/screeners", methods=["POST"])
@require_api_key
def create_screener():
    """POST /api/screeners - Create a custom screener."""
    session = get_session()
    data = request.get_json()

    if not data or not data.get("name") or not data.get("conditions"):
        return jsonify({"error": "name and conditions are required"}), 400

    # Generate slug from name
    slug = data["name"].lower().replace(" ", "-").replace("+", "").replace("&", "and")
    # Ensure uniqueness
    existing = session.query(Screener).filter(Screener.slug == slug).first()
    if existing:
        slug = f"{slug}-{existing.id + 1}"

    screener = Screener(
        name=data["name"],
        slug=slug,
        category=data.get("category"),
        is_builtin=False,
        created_by=g.current_user.id if hasattr(g, "current_user") else None,
        is_active=True,
    )
    session.add(screener)
    session.flush()

    for i, cond in enumerate(data["conditions"]):
        session.add(
            ScreenerCondition(
                screener_id=screener.id,
                field=cond["field"],
                operator=cond["operator"],
                value=cond.get("value"),
                ordinal=i,
            )
        )

    session.commit()

    return jsonify({
        "id": screener.id,
        "name": screener.name,
        "slug": screener.slug,
        "category": screener.category,
    }), 201


@screeners_bp.route("/screeners/preview", methods=["POST"])
@require_api_key
def preview_screener():
    """POST /api/screeners/preview - Run conditions without saving."""
    session = get_session()
    data = request.get_json()

    if not data or not data.get("conditions"):
        return jsonify({"error": "conditions are required"}), 400

    engine = ScreenerEngine(session)
    results = engine.preview(data["conditions"])

    return jsonify({
        "total": len(results),
        "items": results,
    })


@screeners_bp.route("/screeners/<int:screener_id>", methods=["DELETE"])
@require_api_key
def delete_screener(screener_id):
    """DELETE /api/screeners/{id} - Delete a custom screener."""
    session = get_session()

    screener = session.query(Screener).filter(Screener.id == screener_id).first()
    if not screener:
        return jsonify({"error": "Screener not found"}), 404

    if screener.is_builtin:
        return jsonify({"error": "Cannot delete built-in screeners"}), 403

    session.query(ScreenerCondition).filter(
        ScreenerCondition.screener_id == screener_id
    ).delete()
    session.delete(screener)
    session.commit()

    return jsonify({"status": "deleted"})
