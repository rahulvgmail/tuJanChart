"""Event detection engine.

Compares current indicator values to previous day's values to detect
meaningful state transitions (e.g., new 52W high, DMA crossover).
"""

import logging
from datetime import date

from sqlalchemy import desc
from sqlalchemy.orm import Session

from stockpulse.models.event import Event
from stockpulse.models.indicator import StockIndicator

logger = logging.getLogger(__name__)

# Event type constants
EVT_52W_HIGH_INTRADAY = "52W_HIGH_INTRADAY"
EVT_52W_CLOSING_HIGH = "52W_CLOSING_HIGH"
EVT_DMA_CROSSOVER = "DMA_CROSSOVER"
EVT_WMA_CROSSOVER = "WMA_CROSSOVER"
EVT_VOLUME_BREAKOUT = "VOLUME_BREAKOUT"
EVT_GAP_UP = "GAP_UP"
EVT_GAP_DOWN = "GAP_DOWN"
EVT_90D_HIGH = "90D_HIGH"
EVT_90D_LOW = "90D_LOW"
EVT_RESULT_APPROACHING = "RESULT_APPROACHING"
EVT_SCREENER_ENTRY = "SCREENER_ENTRY"
EVT_SCREENER_EXIT = "SCREENER_EXIT"
EVT_ASM_CHANGE = "ASM_CHANGE"


def detect_events(session: Session, stock_id: int, as_of: date) -> list[Event]:
    """Detect technical events by comparing current vs previous indicators.

    Returns list of newly created Event objects (not yet committed).
    """
    # Get current and previous indicator rows
    indicators = (
        session.query(StockIndicator)
        .filter(StockIndicator.stock_id == stock_id, StockIndicator.date <= as_of)
        .order_by(desc(StockIndicator.date))
        .limit(2)
        .all()
    )

    if not indicators:
        return []

    current = indicators[0]
    previous = indicators[1] if len(indicators) > 1 else None

    events = []

    def _add(event_type: str, payload: dict):
        evt = Event(stock_id=stock_id, event_type=event_type, payload=payload)
        session.add(evt)
        events.append(evt)

    # --- 52-Week High ---
    if current.is_52w_high_intraday and (not previous or not previous.is_52w_high_intraday):
        _add(EVT_52W_HIGH_INTRADAY, {
            "price": float(current.today_high) if current.today_high else None,
            "high_52w": float(current.high_52w) if current.high_52w else None,
        })

    if current.is_52w_closing_high and (not previous or not previous.is_52w_closing_high):
        _add(EVT_52W_CLOSING_HIGH, {
            "price": float(current.current_price) if current.current_price else None,
            "high_52w": float(current.high_52w) if current.high_52w else None,
        })

    # --- DMA Crossovers ---
    for period in [10, 20, 50, 100, 200]:
        sig_field = f"dma_{period}_signal"
        touch_field = f"dma_{period}_touch"
        dma_field = f"dma_{period}"

        curr_signal = getattr(current, sig_field)
        prev_signal = getattr(previous, sig_field) if previous else None

        if curr_signal and curr_signal != prev_signal:
            _add(EVT_DMA_CROSSOVER, {
                "period": period,
                "signal": curr_signal,
                "prev_signal": prev_signal,
                "dma_value": float(getattr(current, dma_field)) if getattr(current, dma_field) else None,
                "price": float(current.current_price) if current.current_price else None,
            })

    # --- WMA Crossovers ---
    for period in [5, 10, 20]:
        sig_field = f"wma_{period}_signal"
        wma_field = f"wma_{period}"

        curr_signal = getattr(current, sig_field)
        prev_signal = getattr(previous, sig_field) if previous else None

        if curr_signal and curr_signal != prev_signal:
            _add(EVT_WMA_CROSSOVER, {
                "period": period,
                "signal": curr_signal,
                "prev_signal": prev_signal,
                "wma_value": float(getattr(current, wma_field)) if getattr(current, wma_field) else None,
                "price": float(current.current_price) if current.current_price else None,
            })

    # --- Volume Breakout ---
    if current.is_volume_breakout and (not previous or not previous.is_volume_breakout):
        _add(EVT_VOLUME_BREAKOUT, {
            "volume": current.today_volume,
            "max_vol_21d": current.max_vol_21d,
            "avg_vol_140d": current.avg_vol_140d,
            "price": float(current.current_price) if current.current_price else None,
        })

    # --- Gap Up/Down ---
    if current.is_gap_up:
        _add(EVT_GAP_UP, {
            "gap_pct": float(current.gap_pct) if current.gap_pct else None,
            "open": float(current.today_open) if current.today_open else None,
            "prev_close": float(current.prev_close) if current.prev_close else None,
        })

    if current.is_gap_down:
        _add(EVT_GAP_DOWN, {
            "gap_pct": float(current.gap_pct) if current.gap_pct else None,
            "open": float(current.today_open) if current.today_open else None,
            "prev_close": float(current.prev_close) if current.prev_close else None,
        })

    # --- 90-Day Extremes ---
    if current.is_90d_high and (not previous or not previous.is_90d_high):
        _add(EVT_90D_HIGH, {
            "price": float(current.today_high) if current.today_high else None,
            "high_90d": float(current.high_90d) if current.high_90d else None,
        })

    if current.is_90d_low_touch and (not previous or not previous.is_90d_low_touch):
        _add(EVT_90D_LOW, {
            "price": float(current.today_low) if current.today_low else None,
            "low_90d": float(current.low_90d) if current.low_90d else None,
        })

    # --- Result Approaching ---
    if current.result_within_7d and (not previous or not previous.result_within_7d):
        _add(EVT_RESULT_APPROACHING, {
            "days_to_result": current.days_to_result,
            "window": 7,
        })
    elif current.result_within_10d and (not previous or not previous.result_within_10d):
        _add(EVT_RESULT_APPROACHING, {
            "days_to_result": current.days_to_result,
            "window": 10,
        })
    elif current.result_within_15d and (not previous or not previous.result_within_15d):
        _add(EVT_RESULT_APPROACHING, {
            "days_to_result": current.days_to_result,
            "window": 15,
        })

    if events:
        logger.info("Detected %d events for stock %d on %s", len(events), stock_id, as_of)

    return events


def detect_events_for_universe(session: Session, stock_ids: list[int], as_of: date) -> int:
    """Run event detection for all stocks. Returns total events detected."""
    total = 0
    for stock_id in stock_ids:
        try:
            events = detect_events(session, stock_id, as_of)
            total += len(events)
        except Exception:
            logger.exception("Event detection failed for stock %d", stock_id)

    if total > 0:
        session.commit()
        logger.info("Total events detected: %d for %d stocks", total, len(stock_ids))

    return total
