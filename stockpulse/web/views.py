"""Main web views: dashboard, screeners, stock detail, watchlist."""

from datetime import datetime, timezone

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc, func

from stockpulse.extensions import get_db
from stockpulse.models.annotation import ColorClassification, Note
from stockpulse.models.event import Event
from stockpulse.models.indicator import StockIndicator
from stockpulse.models.screener import Screener, ScreenerCondition
from stockpulse.models.stock import Stock
from stockpulse.models.watchlist import Watchlist

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    session = get_db()
    try:
        # Get latest indicator date
        latest_date_row = (
            session.query(StockIndicator.date)
            .order_by(desc(StockIndicator.date))
            .first()
        )
        latest_date = latest_date_row.date if latest_date_row else None

        summary = {}
        if latest_date:
            # 52W closing highs
            summary["highs_52w"] = (
                session.query(func.count(StockIndicator.id))
                .filter(
                    StockIndicator.date == latest_date,
                    StockIndicator.is_52w_closing_high == True,
                )
                .scalar()
            )
            # Volume breakouts
            summary["volume_breakouts"] = (
                session.query(func.count(StockIndicator.id))
                .filter(
                    StockIndicator.date == latest_date,
                    StockIndicator.is_volume_breakout == True,
                )
                .scalar()
            )
            # Gap ups
            summary["gap_ups"] = (
                session.query(func.count(StockIndicator.id))
                .filter(
                    StockIndicator.date == latest_date,
                    StockIndicator.is_gap_up == True,
                )
                .scalar()
            )
            # 90D highs
            summary["highs_90d"] = (
                session.query(func.count(StockIndicator.id))
                .filter(
                    StockIndicator.date == latest_date,
                    StockIndicator.is_90d_high == True,
                )
                .scalar()
            )
            # Active stocks
            summary["active_stocks"] = (
                session.query(func.count(Stock.id))
                .filter(Stock.is_active == True)
                .scalar()
            )

        # Recent events (last 50)
        recent_events = (
            session.query(Event, Stock)
            .join(Stock, Event.stock_id == Stock.id)
            .order_by(desc(Event.created_at))
            .limit(50)
            .all()
        )

        return render_template(
            "dashboard/index.html",
            summary=summary,
            latest_date=latest_date,
            recent_events=recent_events,
        )
    finally:
        session.close()


@dashboard_bp.route("/dashboard/events-feed")
@login_required
def events_feed():
    """HTMX partial: recent events for polling."""
    session = get_db()
    try:
        recent_events = (
            session.query(Event, Stock)
            .join(Stock, Event.stock_id == Stock.id)
            .order_by(desc(Event.created_at))
            .limit(50)
            .all()
        )
        return render_template("partials/events_feed.html", recent_events=recent_events)
    finally:
        session.close()


# --- Screener Pages ---


@dashboard_bp.route("/screeners")
@login_required
def screener_list():
    session = get_db()
    try:
        screeners = (
            session.query(Screener)
            .filter(Screener.is_active == True)
            .order_by(Screener.category, Screener.name)
            .all()
        )
        # Group by category
        categories = {}
        for s in screeners:
            cat = s.category or "Other"
            categories.setdefault(cat, []).append(s)

        return render_template("screeners/list.html", categories=categories)
    finally:
        session.close()


@dashboard_bp.route("/screeners/<int:screener_id>")
@login_required
def screener_results(screener_id):
    session = get_db()
    try:
        screener = session.query(Screener).filter(Screener.id == screener_id).first()
        if not screener:
            flash("Screener not found.", "error")
            return redirect(url_for("dashboard.screener_list"))

        from stockpulse.engine.screener_engine import ScreenerEngine
        engine = ScreenerEngine(session)

        # Parse extra filters from query string
        extra_filters = {}
        if request.args.get("sector"):
            extra_filters["sector"] = request.args["sector"]
        if request.args.get("color"):
            extra_filters["color"] = request.args["color"]
        if request.args.get("min_pe"):
            extra_filters["min_pe"] = float(request.args["min_pe"])
        if request.args.get("max_pe"):
            extra_filters["max_pe"] = float(request.args["max_pe"])

        results = engine.evaluate(screener_id, extra_filters=extra_filters or None)

        # Sort by user preference
        sort_by = request.args.get("sort", "company_name")
        sort_desc = request.args.get("order", "asc") == "desc"
        results.sort(key=lambda r: r.get(sort_by) or 0, reverse=sort_desc)

        return render_template(
            "screeners/results.html",
            screener=screener,
            results=results,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )
    finally:
        session.close()


@dashboard_bp.route("/screeners/builder", methods=["GET", "POST"])
@login_required
def screener_builder():
    if request.method == "POST":
        session = get_db()
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid request"}), 400

            action = data.get("action", "preview")
            conditions_data = data.get("conditions", [])

            if action == "preview":
                from stockpulse.engine.screener_engine import ScreenerEngine
                engine = ScreenerEngine(session)
                results = engine.preview(conditions_data)
                return render_template("partials/screener_preview.html", results=results)

            elif action == "save":
                name = data.get("name", "").strip()
                if not name:
                    return jsonify({"error": "Name is required"}), 400

                slug = name.lower().replace(" ", "-")
                screener = Screener(
                    name=name,
                    slug=slug,
                    description=data.get("description", ""),
                    is_builtin=False,
                    created_by=current_user.id,
                    category=data.get("category", "custom"),
                )
                session.add(screener)
                session.flush()

                for i, cd in enumerate(conditions_data):
                    session.add(ScreenerCondition(
                        screener_id=screener.id,
                        field=cd["field"],
                        operator=cd["operator"],
                        value=cd.get("value"),
                        ordinal=i,
                    ))

                session.commit()
                return jsonify({"id": screener.id, "slug": screener.slug})
        finally:
            session.close()

    from stockpulse.engine.screener_engine import INDICATOR_FIELDS
    return render_template("screeners/builder.html", fields=sorted(INDICATOR_FIELDS))


# --- Stock Detail ---


@dashboard_bp.route("/stocks/<symbol>")
@login_required
def stock_detail(symbol):
    session = get_db()
    try:
        stock = (
            session.query(Stock)
            .filter((Stock.nse_symbol == symbol) | (Stock.symbol == symbol))
            .first()
        )
        if not stock:
            flash("Stock not found.", "error")
            return redirect(url_for("dashboard.index"))

        # Latest indicator
        indicator = (
            session.query(StockIndicator)
            .filter(StockIndicator.stock_id == stock.id)
            .order_by(desc(StockIndicator.date))
            .first()
        )

        # Current color
        color_row = (
            session.query(ColorClassification)
            .filter(
                ColorClassification.stock_id == stock.id,
                ColorClassification.is_current == True,
            )
            .first()
        )

        # Notes
        notes = (
            session.query(Note)
            .filter(Note.stock_id == stock.id)
            .order_by(desc(Note.created_at))
            .limit(20)
            .all()
        )

        # Recent events
        events = (
            session.query(Event)
            .filter(Event.stock_id == stock.id)
            .order_by(desc(Event.created_at))
            .limit(20)
            .all()
        )

        # Watchlist status
        in_watchlist = False
        if current_user.is_authenticated:
            in_watchlist = (
                session.query(Watchlist)
                .filter(
                    Watchlist.user_id == current_user.id,
                    Watchlist.stock_id == stock.id,
                )
                .first()
            ) is not None

        # Screener memberships
        from stockpulse.models.screener import ScreenerHistory
        memberships = (
            session.query(ScreenerHistory, Screener)
            .join(Screener, ScreenerHistory.screener_id == Screener.id)
            .filter(
                ScreenerHistory.stock_id == stock.id,
                ScreenerHistory.entered == True,
            )
            .order_by(desc(ScreenerHistory.date))
            .limit(20)
            .all()
        )

        return render_template(
            "stocks/detail.html",
            stock=stock,
            indicator=indicator,
            color=color_row.color if color_row else None,
            notes=notes,
            events=events,
            in_watchlist=in_watchlist,
            memberships=memberships,
        )
    finally:
        session.close()


@dashboard_bp.route("/stocks/<symbol>/color", methods=["POST"])
@login_required
def set_color(symbol):
    session = get_db()
    try:
        stock = (
            session.query(Stock)
            .filter((Stock.nse_symbol == symbol) | (Stock.symbol == symbol))
            .first()
        )
        if not stock:
            return jsonify({"error": "Stock not found"}), 404

        new_color = request.form.get("color", "").strip()
        if not new_color:
            return jsonify({"error": "Color is required"}), 400

        # Deactivate current color
        session.query(ColorClassification).filter(
            ColorClassification.stock_id == stock.id,
            ColorClassification.is_current == True,
        ).update({"is_current": False})

        # Add new
        cc = ColorClassification(
            stock_id=stock.id,
            color=new_color,
            assigned_by=current_user.id,
            is_current=True,
        )
        session.add(cc)
        session.commit()
        flash(f"Color set to {new_color}.", "success")
    finally:
        session.close()

    return redirect(url_for("dashboard.stock_detail", symbol=symbol))


@dashboard_bp.route("/stocks/<symbol>/notes", methods=["POST"])
@login_required
def add_note(symbol):
    session = get_db()
    try:
        stock = (
            session.query(Stock)
            .filter((Stock.nse_symbol == symbol) | (Stock.symbol == symbol))
            .first()
        )
        if not stock:
            return jsonify({"error": "Stock not found"}), 404

        content = request.form.get("content", "").strip()
        if not content:
            flash("Note content is required.", "error")
            return redirect(url_for("dashboard.stock_detail", symbol=symbol))

        note = Note(
            stock_id=stock.id,
            author_id=current_user.id,
            author_type="human",
            content=content,
        )
        session.add(note)
        session.commit()
        flash("Note added.", "success")
    finally:
        session.close()

    return redirect(url_for("dashboard.stock_detail", symbol=symbol))


# --- Watchlist ---


@dashboard_bp.route("/watchlist")
@login_required
def watchlist():
    session = get_db()
    try:
        items = (
            session.query(Watchlist, Stock)
            .join(Stock, Watchlist.stock_id == Stock.id)
            .filter(Watchlist.user_id == current_user.id)
            .order_by(Watchlist.added_at.desc())
            .all()
        )

        # Get latest indicators for watchlist stocks
        stock_ids = [item.Watchlist.stock_id for item in items]
        indicators = {}
        if stock_ids:
            latest_date_row = (
                session.query(StockIndicator.date)
                .order_by(desc(StockIndicator.date))
                .first()
            )
            if latest_date_row:
                inds = (
                    session.query(StockIndicator)
                    .filter(
                        StockIndicator.stock_id.in_(stock_ids),
                        StockIndicator.date == latest_date_row.date,
                    )
                    .all()
                )
                indicators = {i.stock_id: i for i in inds}

        return render_template(
            "watchlist/index.html",
            items=items,
            indicators=indicators,
        )
    finally:
        session.close()


@dashboard_bp.route("/watchlist/toggle/<int:stock_id>", methods=["POST"])
@login_required
def toggle_watchlist(stock_id):
    session = get_db()
    try:
        existing = (
            session.query(Watchlist)
            .filter(
                Watchlist.user_id == current_user.id,
                Watchlist.stock_id == stock_id,
            )
            .first()
        )

        if existing:
            session.delete(existing)
            session.commit()
            flash("Removed from watchlist.", "info")
        else:
            session.add(Watchlist(user_id=current_user.id, stock_id=stock_id))
            session.commit()
            flash("Added to watchlist.", "success")
    finally:
        session.close()

    # Redirect back to referrer or stock detail
    next_url = request.referrer or url_for("dashboard.index")
    return redirect(next_url)
