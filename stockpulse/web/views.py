"""Main web views: dashboard, screeners, stock detail, watchlist."""

from datetime import date, datetime, timezone

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc, func

from stockpulse.extensions import get_db
from stockpulse.models.annotation import ColorClassification, Note
from stockpulse.models.event import Event
from stockpulse.models.indicator import StockIndicator
from stockpulse.models.price import DailyPrice
from stockpulse.models.screener import Screener, ScreenerCondition, ScreenerHistory
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

        # Screener links for summary cards
        card_slugs = {
            "highs_52w": "52w-closing-high-today",
            "volume_breakouts": "volume-breakout",
            "gap_ups": "gap-up-today",
            "highs_90d": "90d-high-today",
        }
        card_links = {}
        if summary:
            slug_rows = (
                session.query(Screener.slug, Screener.id)
                .filter(Screener.slug.in_(card_slugs.values()))
                .all()
            )
            slug_to_id = {row.slug: row.id for row in slug_rows}
            for key, slug in card_slugs.items():
                if slug in slug_to_id:
                    card_links[key] = url_for(
                        "dashboard.screener_results", screener_id=slug_to_id[slug]
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
            card_links=card_links,
            latest_date=latest_date,
            recent_events=recent_events,
        )
    finally:
        session.close()


@dashboard_bp.route("/dashboard/ai-cards")
@login_required
def ai_dashboard_partial():
    """HTMX partial: AI summary cards for dashboard."""
    from stockpulse.integrations.tujanalyst_client import TuJanalystClient

    client = TuJanalystClient()
    if not client.is_configured:
        return render_template("partials/ai_dashboard.html", ai_configured=False, stats=None)

    stats = client.get_performance_summary()
    return render_template("partials/ai_dashboard.html", ai_configured=True, stats=stats)


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


@dashboard_bp.route("/screeners/<int:screener_id>/diff")
@login_required
def screener_diff(screener_id):
    """Show stocks that entered/exited a screener, with date navigation."""
    session = get_db()
    try:
        screener = session.query(Screener).filter(Screener.id == screener_id).first()
        if not screener:
            flash("Screener not found.", "error")
            return redirect(url_for("dashboard.screener_list"))

        # Get all dates that have history for this screener
        history_dates = [
            row.date
            for row in session.query(ScreenerHistory.date)
            .filter(ScreenerHistory.screener_id == screener_id)
            .distinct()
            .order_by(desc(ScreenerHistory.date))
            .limit(90)
            .all()
        ]

        if not history_dates:
            return render_template(
                "screeners/diff.html",
                screener=screener,
                as_of=None,
                entries=[],
                exits=[],
                history_dates=[],
                prev_date=None,
                next_date=None,
            )

        # Determine the viewing date
        date_str = request.args.get("date")
        if date_str:
            try:
                as_of = date.fromisoformat(date_str)
            except ValueError:
                as_of = history_dates[0]
        else:
            as_of = history_dates[0]

        # Find prev/next dates for navigation
        prev_date = None
        next_date = None
        if as_of in history_dates:
            idx = history_dates.index(as_of)
            if idx < len(history_dates) - 1:
                prev_date = history_dates[idx + 1]  # older
            if idx > 0:
                next_date = history_dates[idx - 1]  # newer

        # Get entries (entered=True) on this date
        entry_rows = (
            session.query(ScreenerHistory, Stock, StockIndicator)
            .join(Stock, ScreenerHistory.stock_id == Stock.id)
            .outerjoin(
                StockIndicator,
                (StockIndicator.stock_id == ScreenerHistory.stock_id)
                & (StockIndicator.date == ScreenerHistory.date),
            )
            .filter(
                ScreenerHistory.screener_id == screener_id,
                ScreenerHistory.date == as_of,
                ScreenerHistory.entered == True,
            )
            .all()
        )

        # Get exits (entered=False) on this date
        exit_rows = (
            session.query(ScreenerHistory, Stock, StockIndicator)
            .join(Stock, ScreenerHistory.stock_id == Stock.id)
            .outerjoin(
                StockIndicator,
                (StockIndicator.stock_id == ScreenerHistory.stock_id)
                & (StockIndicator.date == ScreenerHistory.date),
            )
            .filter(
                ScreenerHistory.screener_id == screener_id,
                ScreenerHistory.date == as_of,
                ScreenerHistory.entered == False,
            )
            .all()
        )

        def _row_to_dict(history, stock, indicator):
            d = {
                "symbol": stock.nse_symbol or stock.symbol,
                "company_name": stock.company_name,
                "sector": stock.sector,
            }
            if indicator:
                d.update(
                    current_price=float(indicator.current_price) if indicator.current_price else None,
                    pct_change=float(indicator.pct_change) if indicator.pct_change else None,
                    today_volume=indicator.today_volume,
                    dma_10=float(indicator.dma_10) if indicator.dma_10 else None,
                    dma_10_signal=indicator.dma_10_signal,
                    dma_20=float(indicator.dma_20) if indicator.dma_20 else None,
                    dma_20_signal=indicator.dma_20_signal,
                    dma_50=float(indicator.dma_50) if indicator.dma_50 else None,
                    dma_50_signal=indicator.dma_50_signal,
                )
            return d

        entries = [_row_to_dict(*row) for row in entry_rows]
        exits = [_row_to_dict(*row) for row in exit_rows]

        # Count how many stocks are currently in the screener on this date
        total_in = (
            session.query(func.count(ScreenerHistory.id))
            .filter(
                ScreenerHistory.screener_id == screener_id,
                ScreenerHistory.date == as_of,
                ScreenerHistory.entered == True,
            )
            .scalar()
        )

        return render_template(
            "screeners/diff.html",
            screener=screener,
            as_of=as_of,
            entries=entries,
            exits=exits,
            total_in=total_in,
            history_dates=history_dates[:30],
            prev_date=prev_date,
            next_date=next_date,
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


@dashboard_bp.route("/stocks/<symbol>/prices.json")
@login_required
def stock_prices_json(symbol):
    """JSON endpoint for chart data (session-auth, no API key needed)."""
    from datetime import date, timedelta

    session = get_db()
    try:
        stock = (
            session.query(Stock)
            .filter((Stock.nse_symbol == symbol) | (Stock.symbol == symbol))
            .first()
        )
        if not stock:
            return jsonify({"error": "Stock not found"}), 404

        period_str = request.args.get("period", "365d")
        try:
            days = int(period_str.rstrip("d"))
        except ValueError:
            days = 365

        cutoff = date.today() - timedelta(days=days)

        prices = (
            session.query(DailyPrice)
            .filter(DailyPrice.stock_id == stock.id, DailyPrice.date >= cutoff)
            .order_by(DailyPrice.date)
            .all()
        )

        return jsonify([
            {
                "time": p.date.isoformat(),
                "open": float(p.open) if p.open else None,
                "high": float(p.high) if p.high else None,
                "low": float(p.low) if p.low else None,
                "close": float(p.close) if p.close else None,
                "volume": int(p.volume) if p.volume else None,
            }
            for p in prices
        ])
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


# --- AI Analysis Partial ---


@dashboard_bp.route("/stocks/<symbol>/ai")
@login_required
def stock_ai_partial(symbol):
    """HTMX partial: AI analysis data from tuJanalyst."""
    from stockpulse.integrations.tujanalyst_client import TuJanalystClient

    client = TuJanalystClient()
    if not client.is_configured:
        return render_template("partials/ai_analysis.html", ai_configured=False)

    investigation = client.get_latest_investigation(symbol)
    investigations = client.get_investigations(symbol, limit=5)
    position = client.get_position(symbol)

    return render_template(
        "partials/ai_analysis.html",
        ai_configured=True,
        investigation=investigation,
        investigations=investigations,
        position=position,
    )


# --- AI Reports ---


@dashboard_bp.route("/reports")
@login_required
def reports_list():
    """Browse AI-generated reports from tuJanalyst."""
    from stockpulse.integrations.tujanalyst_client import TuJanalystClient

    client = TuJanalystClient()
    if not client.is_configured:
        return render_template("reports/index.html", ai_configured=False, reports=[])

    reports = client.get_reports(limit=50)
    return render_template("reports/index.html", ai_configured=True, reports=reports)


@dashboard_bp.route("/reports/<report_id>")
@login_required
def report_detail(report_id):
    """View a single AI report."""
    from stockpulse.integrations.tujanalyst_client import TuJanalystClient

    client = TuJanalystClient()
    if not client.is_configured:
        return render_template("reports/detail.html", report=None)

    report = client.get_report(report_id)
    return render_template("reports/detail.html", report=report)


# --- AI Performance ---


@dashboard_bp.route("/performance")
@login_required
def performance_dashboard():
    """AI recommendation performance tracking dashboard."""
    from stockpulse.integrations.tujanalyst_client import TuJanalystClient

    client = TuJanalystClient()
    if not client.is_configured:
        return render_template(
            "performance/index.html", ai_configured=False, summary=None, recommendations=[],
        )

    summary = client.get_performance_summary()
    recommendations = client.get_performance_recommendations(limit=100)
    return render_template(
        "performance/index.html",
        ai_configured=True,
        summary=summary,
        recommendations=recommendations,
    )


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
