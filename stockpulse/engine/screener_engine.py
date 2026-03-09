"""Composable screener engine.

Translates screener conditions into SQLAlchemy WHERE clauses and
evaluates them against the stock_indicators table.
"""

import logging
from datetime import date

from sqlalchemy import and_, or_, desc
from sqlalchemy.orm import Session

from stockpulse.models.annotation import ColorClassification
from stockpulse.models.indicator import StockIndicator
from stockpulse.models.screener import Screener, ScreenerCondition, ScreenerHistory
from stockpulse.models.stock import Stock

logger = logging.getLogger(__name__)

# Map condition field names to StockIndicator columns
INDICATOR_FIELDS = {
    # Price
    "current_price", "prev_close", "pct_change", "pe", "market_cap_cr",
    "today_high", "today_low", "today_open", "today_volume",
    # DMAs
    "dma_10", "dma_20", "dma_50", "dma_100", "dma_200",
    "dma_10_touch", "dma_20_touch", "dma_50_touch", "dma_100_touch", "dma_200_touch",
    "dma_10_signal", "dma_20_signal", "dma_50_signal", "dma_100_signal", "dma_200_signal",
    # WMAs
    "wma_5", "wma_10", "wma_20", "wma_30",
    "wma_5_touch", "wma_10_touch", "wma_20_touch",
    "wma_5_signal", "wma_10_signal", "wma_20_signal",
    # 52W
    "high_52w", "is_52w_high_intraday", "is_52w_closing_high",
    "was_52w_high_yesterday", "prev_52w_closing_high", "high_52w_date",
    # Volume
    "max_vol_21d", "avg_vol_140d", "avg_vol_280d", "is_volume_breakout",
    # Biweek/Week
    "biweek_high", "biweek_vol", "is_biweek_bo",
    "week_high", "week_vol", "is_week_bo",
    # Gap
    "gap_pct", "is_gap_up", "is_gap_down",
    # 90D
    "high_90d", "low_90d", "is_90d_high", "is_90d_low_touch",
    # Result
    "days_to_result", "result_within_7d", "result_within_10d",
    "result_within_15d", "result_declared_10d",
}

# Fields that come from other tables
SPECIAL_FIELDS = {"color"}


def _build_condition_clause(condition: ScreenerCondition):
    """Translate a single ScreenerCondition into a SQLAlchemy clause.

    Returns a clause that can be used in a WHERE statement, or None
    if the condition references the color field (handled separately).
    """
    field = condition.field
    op = condition.operator
    value = condition.value

    # Handle color field specially
    if field == "color":
        return _build_color_clause(op, value)

    if field not in INDICATOR_FIELDS:
        logger.warning("Unknown screener field: %s", field)
        return None

    column = getattr(StockIndicator, field)

    if op == "is_true":
        return column == True
    elif op == "is_false":
        return column == False
    elif op == "eq":
        return column == value
    elif op == "neq":
        return column != value
    elif op == "gt":
        return column > value
    elif op == "gte":
        return column >= value
    elif op == "lt":
        return column < value
    elif op == "lte":
        return column <= value
    elif op == "in":
        if isinstance(value, list):
            return column.in_(value)
        return column == value
    elif op == "between":
        if isinstance(value, list) and len(value) == 2:
            return column.between(value[0], value[1])
        return None
    elif op == "gt_field":
        # Relative comparison: field > other_field
        if isinstance(value, str) and value in INDICATOR_FIELDS:
            other_col = getattr(StockIndicator, value)
            return column > other_col
        return None
    elif op == "lt_field":
        if isinstance(value, str) and value in INDICATOR_FIELDS:
            other_col = getattr(StockIndicator, value)
            return column < other_col
        return None
    elif op == "gte_field":
        if isinstance(value, str) and value in INDICATOR_FIELDS:
            other_col = getattr(StockIndicator, value)
            return column >= other_col
        return None
    else:
        logger.warning("Unknown operator: %s", op)
        return None


def _build_color_clause(op: str, value):
    """Build a clause for the color field, which lives in color_classifications."""
    if op == "eq":
        return ColorClassification.color == value
    elif op == "in":
        if isinstance(value, list):
            return ColorClassification.color.in_(value)
        return ColorClassification.color == value
    elif op == "neq":
        return ColorClassification.color != value
    return None


class ScreenerEngine:
    """Evaluates screener definitions against indicator data."""

    def __init__(self, session: Session):
        self.session = session

    def evaluate(
        self,
        screener_id: int,
        as_of: date | None = None,
        extra_filters: dict | None = None,
    ) -> list[dict]:
        """Run a screener and return matching stocks with indicators.

        Args:
            screener_id: The screener to evaluate.
            as_of: Date to evaluate against (defaults to latest available).
            extra_filters: Optional API-level filters like {min_pe, max_pe, color, sector}.

        Returns:
            List of dicts with stock info + indicator values for matching stocks.
        """
        screener = self.session.query(Screener).filter(Screener.id == screener_id).first()
        if not screener:
            logger.warning("Screener %d not found", screener_id)
            return []

        conditions = (
            self.session.query(ScreenerCondition)
            .filter(ScreenerCondition.screener_id == screener_id)
            .order_by(ScreenerCondition.ordinal)
            .all()
        )

        return self._run_conditions(conditions, as_of, extra_filters)

    def preview(
        self,
        conditions_data: list[dict],
        as_of: date | None = None,
    ) -> list[dict]:
        """Run ad-hoc conditions without saving (for the screener builder).

        Args:
            conditions_data: List of dicts with {field, operator, value}.
        """
        # Convert dicts to ScreenerCondition-like objects
        conditions = []
        for i, cd in enumerate(conditions_data):
            cond = ScreenerCondition(
                field=cd["field"],
                operator=cd["operator"],
                value=cd.get("value"),
                ordinal=i,
            )
            conditions.append(cond)

        return self._run_conditions(conditions, as_of)

    def _run_conditions(
        self,
        conditions: list[ScreenerCondition],
        as_of: date | None = None,
        extra_filters: dict | None = None,
    ) -> list[dict]:
        """Build and execute the query for a set of conditions."""
        # Determine the target date
        if as_of is None:
            latest = (
                self.session.query(StockIndicator.date)
                .order_by(desc(StockIndicator.date))
                .first()
            )
            if not latest:
                return []
            as_of = latest.date

        # Check if any condition references color
        needs_color_join = any(c.field == "color" for c in conditions)
        if extra_filters and "color" in extra_filters:
            needs_color_join = True

        # Build base query
        query = (
            self.session.query(StockIndicator, Stock)
            .join(Stock, StockIndicator.stock_id == Stock.id)
            .filter(
                StockIndicator.date == as_of,
                Stock.is_active == True,
            )
        )

        if needs_color_join:
            query = query.outerjoin(
                ColorClassification,
                and_(
                    ColorClassification.stock_id == Stock.id,
                    ColorClassification.is_current == True,
                ),
            )

        # Apply screener conditions (AND logic)
        for cond in conditions:
            clause = _build_condition_clause(cond)
            if clause is not None:
                query = query.filter(clause)

        # Apply extra API-level filters
        if extra_filters:
            if "min_pe" in extra_filters and extra_filters["min_pe"] is not None:
                query = query.filter(StockIndicator.pe >= extra_filters["min_pe"])
            if "max_pe" in extra_filters and extra_filters["max_pe"] is not None:
                query = query.filter(StockIndicator.pe <= extra_filters["max_pe"])
            if "min_mcap" in extra_filters and extra_filters["min_mcap"] is not None:
                query = query.filter(StockIndicator.market_cap_cr >= extra_filters["min_mcap"])
            if "max_mcap" in extra_filters and extra_filters["max_mcap"] is not None:
                query = query.filter(StockIndicator.market_cap_cr <= extra_filters["max_mcap"])
            if "sector" in extra_filters and extra_filters["sector"]:
                query = query.filter(Stock.sector == extra_filters["sector"])
            if "color" in extra_filters and extra_filters["color"]:
                if not needs_color_join:
                    query = query.outerjoin(
                        ColorClassification,
                        and_(
                            ColorClassification.stock_id == Stock.id,
                            ColorClassification.is_current == True,
                        ),
                    )
                colors = extra_filters["color"]
                if isinstance(colors, str):
                    colors = [colors]
                query = query.filter(ColorClassification.color.in_(colors))

        # Execute
        results = query.all()

        return [
            _indicator_to_dict(indicator, stock)
            for indicator, stock in results
        ]

    def record_history(self, screener_id: int, as_of: date) -> dict:
        """Record which stocks match a screener on a given date.

        Compares to previous date to detect entries and exits.
        Returns {entered: int, exited: int}.
        """
        # Get current matches
        current_results = self.evaluate(screener_id, as_of)
        current_ids = {r["stock_id"] for r in current_results}

        # Get previous date's matches from history
        prev_record = (
            self.session.query(ScreenerHistory.stock_id)
            .filter(
                ScreenerHistory.screener_id == screener_id,
                ScreenerHistory.date < as_of,
                ScreenerHistory.entered == True,
            )
            .order_by(desc(ScreenerHistory.date))
            .all()
        )
        # Get the most recent history date
        prev_date_row = (
            self.session.query(ScreenerHistory.date)
            .filter(
                ScreenerHistory.screener_id == screener_id,
                ScreenerHistory.date < as_of,
            )
            .order_by(desc(ScreenerHistory.date))
            .first()
        )

        prev_ids = set()
        if prev_date_row:
            prev_ids = {
                r.stock_id
                for r in self.session.query(ScreenerHistory.stock_id)
                .filter(
                    ScreenerHistory.screener_id == screener_id,
                    ScreenerHistory.date == prev_date_row.date,
                    ScreenerHistory.entered == True,
                )
                .all()
            }

        entered = current_ids - prev_ids
        exited = prev_ids - current_ids

        # Record entries
        for sid in entered:
            self.session.add(
                ScreenerHistory(
                    screener_id=screener_id,
                    stock_id=sid,
                    date=as_of,
                    entered=True,
                )
            )

        # Record exits
        for sid in exited:
            self.session.add(
                ScreenerHistory(
                    screener_id=screener_id,
                    stock_id=sid,
                    date=as_of,
                    entered=False,
                )
            )

        return {"entered": len(entered), "exited": len(exited)}


def _indicator_to_dict(indicator: StockIndicator, stock: Stock) -> dict:
    """Convert indicator + stock to a flat dict for API/UI consumption."""
    return {
        "stock_id": stock.id,
        "symbol": stock.symbol,
        "nse_symbol": stock.nse_symbol,
        "company_name": stock.company_name,
        "sector": stock.sector,
        "date": indicator.date.isoformat(),
        "current_price": float(indicator.current_price) if indicator.current_price else None,
        "prev_close": float(indicator.prev_close) if indicator.prev_close else None,
        "pct_change": float(indicator.pct_change) if indicator.pct_change else None,
        "pe": float(indicator.pe) if indicator.pe else None,
        "market_cap_cr": float(indicator.market_cap_cr) if indicator.market_cap_cr else None,
        "today_high": float(indicator.today_high) if indicator.today_high else None,
        "today_low": float(indicator.today_low) if indicator.today_low else None,
        "today_volume": indicator.today_volume,
        # DMAs
        "dma_10": float(indicator.dma_10) if indicator.dma_10 else None,
        "dma_20": float(indicator.dma_20) if indicator.dma_20 else None,
        "dma_50": float(indicator.dma_50) if indicator.dma_50 else None,
        "dma_100": float(indicator.dma_100) if indicator.dma_100 else None,
        "dma_200": float(indicator.dma_200) if indicator.dma_200 else None,
        "dma_10_touch": indicator.dma_10_touch,
        "dma_20_touch": indicator.dma_20_touch,
        "dma_50_touch": indicator.dma_50_touch,
        "dma_100_touch": indicator.dma_100_touch,
        "dma_200_touch": indicator.dma_200_touch,
        "dma_10_signal": indicator.dma_10_signal,
        "dma_20_signal": indicator.dma_20_signal,
        "dma_50_signal": indicator.dma_50_signal,
        "dma_100_signal": indicator.dma_100_signal,
        "dma_200_signal": indicator.dma_200_signal,
        # WMAs
        "wma_5": float(indicator.wma_5) if indicator.wma_5 else None,
        "wma_10": float(indicator.wma_10) if indicator.wma_10 else None,
        "wma_20": float(indicator.wma_20) if indicator.wma_20 else None,
        "wma_30": float(indicator.wma_30) if indicator.wma_30 else None,
        "wma_5_touch": indicator.wma_5_touch,
        "wma_10_touch": indicator.wma_10_touch,
        "wma_20_touch": indicator.wma_20_touch,
        "wma_5_signal": indicator.wma_5_signal,
        "wma_10_signal": indicator.wma_10_signal,
        "wma_20_signal": indicator.wma_20_signal,
        # 52W
        "high_52w": float(indicator.high_52w) if indicator.high_52w else None,
        "is_52w_high_intraday": indicator.is_52w_high_intraday,
        "is_52w_closing_high": indicator.is_52w_closing_high,
        "was_52w_high_yesterday": indicator.was_52w_high_yesterday,
        "high_52w_date": indicator.high_52w_date.isoformat() if indicator.high_52w_date else None,
        # Volume
        "max_vol_21d": indicator.max_vol_21d,
        "avg_vol_140d": indicator.avg_vol_140d,
        "avg_vol_280d": indicator.avg_vol_280d,
        "is_volume_breakout": indicator.is_volume_breakout,
        # Biweek/Week
        "biweek_high": float(indicator.biweek_high) if indicator.biweek_high else None,
        "is_biweek_bo": indicator.is_biweek_bo,
        "week_high": float(indicator.week_high) if indicator.week_high else None,
        "is_week_bo": indicator.is_week_bo,
        # Gap
        "gap_pct": float(indicator.gap_pct) if indicator.gap_pct else None,
        "is_gap_up": indicator.is_gap_up,
        "is_gap_down": indicator.is_gap_down,
        # 90D
        "high_90d": float(indicator.high_90d) if indicator.high_90d else None,
        "low_90d": float(indicator.low_90d) if indicator.low_90d else None,
        "is_90d_high": indicator.is_90d_high,
        "is_90d_low_touch": indicator.is_90d_low_touch,
        # Result
        "days_to_result": indicator.days_to_result,
        "result_within_7d": indicator.result_within_7d,
        "result_within_10d": indicator.result_within_10d,
        "result_within_15d": indicator.result_within_15d,
        "result_declared_10d": indicator.result_declared_10d,
    }
