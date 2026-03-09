"""Technical indicator computation engine.

Computes all 40+ indicators for a stock on a given date, matching
the spreadsheet's Final sheet formulas within 0.01% tolerance.
"""

import logging
from datetime import date, timedelta

import numpy as np
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from stockpulse.engine.signals import compute_touch_and_signal
from stockpulse.models.corporate_action import ResultDate
from stockpulse.models.indicator import StockIndicator
from stockpulse.models.price import DailyPrice, WeeklyPrice

logger = logging.getLogger(__name__)


def _fetch_daily_closes(
    session: Session, stock_id: int, as_of: date, n: int
) -> np.ndarray:
    """Fetch last N daily closing prices up to and including as_of date."""
    rows = (
        session.query(DailyPrice.close)
        .filter(DailyPrice.stock_id == stock_id, DailyPrice.date <= as_of)
        .order_by(desc(DailyPrice.date))
        .limit(n)
        .all()
    )
    return np.array([float(r.close) for r in rows if r.close is not None])


def _fetch_daily_data(
    session: Session, stock_id: int, as_of: date, n: int
) -> list[DailyPrice]:
    """Fetch last N daily price records up to and including as_of date."""
    return (
        session.query(DailyPrice)
        .filter(DailyPrice.stock_id == stock_id, DailyPrice.date <= as_of)
        .order_by(desc(DailyPrice.date))
        .limit(n)
        .all()
    )


def _fetch_weekly_closes(
    session: Session, stock_id: int, as_of: date, n: int
) -> np.ndarray:
    """Fetch last N weekly closing prices up to and including as_of date."""
    rows = (
        session.query(WeeklyPrice.close)
        .filter(WeeklyPrice.stock_id == stock_id, WeeklyPrice.week_ending <= as_of)
        .order_by(desc(WeeklyPrice.week_ending))
        .limit(n)
        .all()
    )
    return np.array([float(r.close) for r in rows if r.close is not None])


def _fetch_weekly_data(
    session: Session, stock_id: int, as_of: date, n: int
) -> list[WeeklyPrice]:
    """Fetch last N weekly price records."""
    return (
        session.query(WeeklyPrice)
        .filter(WeeklyPrice.stock_id == stock_id, WeeklyPrice.week_ending <= as_of)
        .order_by(desc(WeeklyPrice.week_ending))
        .limit(n)
        .all()
    )


def compute_dma(closes: np.ndarray, period: int) -> float | None:
    """Compute Daily Moving Average.

    DMA(N) = arithmetic mean of last N daily closes including current day.
    If fewer than N points, compute from available and flag.
    """
    if len(closes) == 0:
        return None
    n = min(period, len(closes))
    return float(np.mean(closes[:n]))


def compute_wma(closes: np.ndarray, period: int) -> float | None:
    """Compute Weekly Moving Average.

    WMA(N) = arithmetic mean of last N weekly closes.
    """
    if len(closes) == 0:
        return None
    n = min(period, len(closes))
    return float(np.mean(closes[:n]))


def compute_52w_metrics(
    session: Session, stock_id: int, as_of: date, today_high: float | None, today_close: float | None
) -> dict:
    """Compute 52-week high metrics.

    Uses 252 trading days of data.
    """
    daily_data = _fetch_daily_data(session, stock_id, as_of, 252)

    if not daily_data:
        return {
            "high_52w": None,
            "is_52w_high_intraday": False,
            "is_52w_closing_high": False,
            "was_52w_high_yesterday": False,
            "prev_52w_closing_high": None,
            "high_52w_date": None,
        }

    # All highs over 252 trading days
    highs = [float(d.high) for d in daily_data if d.high is not None]
    closes = [float(d.close) for d in daily_data if d.close is not None]

    high_52w = max(highs) if highs else None
    max_close_52w = max(closes) if closes else None

    # Find the date of 52W high
    high_52w_date = None
    if high_52w is not None:
        for d in daily_data:
            if d.high is not None and float(d.high) == high_52w:
                high_52w_date = d.date
                break

    # Intraday 52W high: today's high equals the 52W high
    is_52w_high_intraday = (
        today_high is not None and high_52w is not None and today_high >= high_52w
    )

    # Closing 52W high: today's close >= max close over 252 days
    is_52w_closing_high = (
        today_close is not None and max_close_52w is not None and today_close >= max_close_52w
    )

    # Yesterday's 52W closing high: was the previous day's close the 52W closing high?
    was_52w_high_yesterday = False
    prev_52w_closing_high = None
    if len(daily_data) >= 2:
        yesterday = daily_data[1]  # index 0 is today, 1 is yesterday
        prev_closes = [float(d.close) for d in daily_data[1:] if d.close is not None]
        if prev_closes and yesterday.close is not None:
            prev_max = max(prev_closes)
            prev_52w_closing_high = prev_max
            was_52w_high_yesterday = float(yesterday.close) >= prev_max

    return {
        "high_52w": high_52w,
        "is_52w_high_intraday": is_52w_high_intraday,
        "is_52w_closing_high": is_52w_closing_high,
        "was_52w_high_yesterday": was_52w_high_yesterday,
        "prev_52w_closing_high": prev_52w_closing_high,
        "high_52w_date": high_52w_date,
    }


def compute_volume_metrics(
    daily_data: list[DailyPrice],
    today_volume: int | None,
    max_period: int = 21,
    avg_short_period: int = 140,
    avg_long_period: int = 280,
) -> dict:
    """Compute volume analytics and breakout detection.

    Volume breakout: today's volume > max_vol_21d OR > avg_vol_140d OR > avg_vol_280d
    """
    volumes = [int(d.volume) for d in daily_data if d.volume is not None]

    max_vol_21d = max(volumes[:max_period]) if len(volumes) >= max_period else (max(volumes) if volumes else None)
    avg_vol_140d = int(np.mean(volumes[:avg_short_period])) if len(volumes) >= avg_short_period else (int(np.mean(volumes)) if volumes else None)
    avg_vol_280d = int(np.mean(volumes[:avg_long_period])) if len(volumes) >= avg_long_period else (int(np.mean(volumes)) if volumes else None)

    is_breakout = False
    if today_volume is not None:
        if max_vol_21d is not None and today_volume > max_vol_21d:
            is_breakout = True
        elif avg_vol_140d is not None and today_volume > avg_vol_140d:
            is_breakout = True
        elif avg_vol_280d is not None and today_volume > avg_vol_280d:
            is_breakout = True

    return {
        "max_vol_21d": max_vol_21d,
        "avg_vol_140d": avg_vol_140d,
        "avg_vol_280d": avg_vol_280d,
        "is_volume_breakout": is_breakout,
    }


def compute_gap(
    today_open: float | None, prev_close: float | None, threshold: float = 3.0
) -> dict:
    """Compute gap-up/gap-down.

    gap_pct = (today_open - prev_close) / prev_close * 100
    """
    if today_open is None or prev_close is None or prev_close == 0:
        return {
            "gap_pct": None,
            "is_gap_up": False,
            "is_gap_down": False,
        }

    gap_pct = (today_open - prev_close) / prev_close * 100

    return {
        "gap_pct": round(gap_pct, 4),
        "is_gap_up": gap_pct > threshold,
        "is_gap_down": gap_pct < -threshold,
    }


def compute_90d_extremes(
    session: Session, stock_id: int, as_of: date,
    today_high: float | None, today_low: float | None,
) -> dict:
    """Compute 90-day high and low from weekly data.

    Also checks if today touches the 90-day low.
    """
    # Use ~13 weeks of weekly data for 90 days
    weekly_data = _fetch_weekly_data(session, stock_id, as_of, 13)

    if not weekly_data:
        return {
            "high_90d": None,
            "low_90d": None,
            "is_90d_high": False,
            "is_90d_low_touch": False,
        }

    highs = [float(w.high) for w in weekly_data if w.high is not None]
    lows = [float(w.low) for w in weekly_data if w.low is not None]

    high_90d = max(highs) if highs else None
    low_90d = min(lows) if lows else None

    is_90d_high = today_high is not None and high_90d is not None and today_high >= high_90d
    is_90d_low_touch = today_low is not None and low_90d is not None and today_low <= low_90d

    return {
        "high_90d": high_90d,
        "low_90d": low_90d,
        "is_90d_high": is_90d_high,
        "is_90d_low_touch": is_90d_low_touch,
    }


def compute_biweekly_breakout(daily_data: list[DailyPrice]) -> dict:
    """Compute biweekly (10 trading days) high and volume breakout."""
    if len(daily_data) < 10:
        return {
            "biweek_high": None,
            "biweek_vol": None,
            "is_biweek_bo": False,
        }

    biweek = daily_data[:10]
    biweek_high = max(float(d.high) for d in biweek if d.high is not None) if any(d.high for d in biweek) else None
    biweek_vol = max(int(d.volume) for d in biweek if d.volume is not None) if any(d.volume for d in biweek) else None

    # Compare to prior biweek
    prior = daily_data[10:20] if len(daily_data) >= 20 else []
    is_bo = False
    if prior and biweek_high is not None:
        prior_high = max(float(d.high) for d in prior if d.high is not None) if any(d.high for d in prior) else None
        if prior_high and biweek_high > prior_high:
            is_bo = True

    return {
        "biweek_high": biweek_high,
        "biweek_vol": biweek_vol,
        "is_biweek_bo": is_bo,
    }


def compute_weekly_breakout(weekly_data: list[WeeklyPrice]) -> dict:
    """Compute weekly high and volume breakout."""
    if not weekly_data:
        return {
            "week_high": None,
            "week_vol": None,
            "is_week_bo": False,
        }

    current = weekly_data[0]
    week_high = float(current.high) if current.high else None
    week_vol = int(current.volume) if current.volume else None

    # Compare to prior week
    is_bo = False
    if len(weekly_data) >= 2:
        prior = weekly_data[1]
        if week_high and prior.high and week_high > float(prior.high):
            if week_vol and prior.volume and week_vol > int(prior.volume):
                is_bo = True

    return {
        "week_high": week_high,
        "week_vol": week_vol,
        "is_week_bo": is_bo,
    }


def compute_result_proximity(
    session: Session, stock_id: int, as_of: date,
    window_short: int = 7, window_medium: int = 10,
    window_long: int = 15, declared_window: int = 10,
) -> dict:
    """Compute result date proximity indicators.

    - days_to_result: calendar days to nearest upcoming result date
    - result_within_Nd: True if result is within N days
    - result_declared_10d: True if result was in last 10 days
    """
    # Find nearest upcoming result date
    upcoming = (
        session.query(ResultDate)
        .filter(ResultDate.stock_id == stock_id, ResultDate.result_date >= as_of)
        .order_by(ResultDate.result_date)
        .first()
    )

    # Find most recent past result date
    past = (
        session.query(ResultDate)
        .filter(ResultDate.stock_id == stock_id, ResultDate.result_date < as_of)
        .order_by(desc(ResultDate.result_date))
        .first()
    )

    days_to_result = None
    result_within_7d = False
    result_within_10d = False
    result_within_15d = False
    result_declared_10d = False

    if upcoming and upcoming.result_date:
        days_to_result = (upcoming.result_date - as_of).days
        result_within_7d = days_to_result <= window_short
        result_within_10d = days_to_result <= window_medium
        result_within_15d = days_to_result <= window_long

    if past and past.result_date:
        days_since = (as_of - past.result_date).days
        result_declared_10d = days_since <= declared_window

    return {
        "days_to_result": days_to_result,
        "result_within_7d": result_within_7d,
        "result_within_10d": result_within_10d,
        "result_within_15d": result_within_15d,
        "result_declared_10d": result_declared_10d,
    }


def compute_all_indicators(
    session: Session,
    stock_id: int,
    as_of: date,
    gap_threshold: float = 3.0,
    vol_max_period: int = 21,
    vol_avg_short: int = 140,
    vol_avg_long: int = 280,
) -> StockIndicator | None:
    """Compute all indicators for a stock on a given date.

    This is the main orchestrator that calls all compute functions
    and returns a populated StockIndicator object.
    """
    # Fetch today's price data
    today_price = (
        session.query(DailyPrice)
        .filter(DailyPrice.stock_id == stock_id, DailyPrice.date == as_of)
        .first()
    )

    if not today_price or today_price.close is None:
        logger.debug("No price data for stock %d on %s", stock_id, as_of)
        return None

    current_price = float(today_price.close)
    today_high = float(today_price.high) if today_price.high else None
    today_low = float(today_price.low) if today_price.low else None
    today_open = float(today_price.open) if today_price.open else None
    today_volume = int(today_price.volume) if today_price.volume else None

    # Previous day's close
    prev_day = (
        session.query(DailyPrice)
        .filter(DailyPrice.stock_id == stock_id, DailyPrice.date < as_of)
        .order_by(desc(DailyPrice.date))
        .first()
    )
    prev_close = float(prev_day.close) if prev_day and prev_day.close else None

    # Percent change
    pct_change = None
    if prev_close and prev_close > 0:
        pct_change = round((current_price - prev_close) / prev_close * 100, 4)

    # ---- Daily Moving Averages ----
    daily_closes = _fetch_daily_closes(session, stock_id, as_of, 200)
    dma_10 = compute_dma(daily_closes, 10)
    dma_20 = compute_dma(daily_closes, 20)
    dma_50 = compute_dma(daily_closes, 50)
    dma_100 = compute_dma(daily_closes, 100)
    dma_200 = compute_dma(daily_closes, 200)

    # DMA touch and signals
    dma_10_touch, dma_10_signal = compute_touch_and_signal(current_price, today_high, today_low, dma_10)
    dma_20_touch, dma_20_signal = compute_touch_and_signal(current_price, today_high, today_low, dma_20)
    dma_50_touch, dma_50_signal = compute_touch_and_signal(current_price, today_high, today_low, dma_50)
    dma_100_touch, dma_100_signal = compute_touch_and_signal(current_price, today_high, today_low, dma_100)
    dma_200_touch, dma_200_signal = compute_touch_and_signal(current_price, today_high, today_low, dma_200)

    # ---- Weekly Moving Averages ----
    weekly_closes = _fetch_weekly_closes(session, stock_id, as_of, 30)
    wma_5 = compute_wma(weekly_closes, 5)
    wma_10 = compute_wma(weekly_closes, 10)
    wma_20 = compute_wma(weekly_closes, 20)
    wma_30 = compute_wma(weekly_closes, 30)

    # WMA touch and signals
    wma_5_touch, wma_5_signal = compute_touch_and_signal(current_price, today_high, today_low, wma_5)
    wma_10_touch, wma_10_signal = compute_touch_and_signal(current_price, today_high, today_low, wma_10)
    wma_20_touch, wma_20_signal = compute_touch_and_signal(current_price, today_high, today_low, wma_20)

    # ---- 52-Week Metrics ----
    metrics_52w = compute_52w_metrics(session, stock_id, as_of, today_high, current_price)

    # ---- Volume ----
    daily_data = _fetch_daily_data(session, stock_id, as_of, vol_avg_long)
    vol_metrics = compute_volume_metrics(
        daily_data, today_volume, vol_max_period, vol_avg_short, vol_avg_long
    )

    # ---- Gap ----
    gap = compute_gap(today_open, prev_close, gap_threshold)

    # ---- 90-Day Extremes ----
    extremes_90d = compute_90d_extremes(session, stock_id, as_of, today_high, today_low)

    # ---- Biweekly/Weekly Breakout ----
    biweek = compute_biweekly_breakout(daily_data)
    weekly_data = _fetch_weekly_data(session, stock_id, as_of, 4)
    week_bo = compute_weekly_breakout(weekly_data)

    # ---- Result Date Proximity ----
    result_prox = compute_result_proximity(session, stock_id, as_of)

    # ---- Upsert indicator row ----
    indicator = (
        session.query(StockIndicator)
        .filter(StockIndicator.stock_id == stock_id, StockIndicator.date == as_of)
        .first()
    )

    if not indicator:
        indicator = StockIndicator(stock_id=stock_id, date=as_of)
        session.add(indicator)

    # Populate all fields
    indicator.current_price = current_price
    indicator.prev_close = prev_close
    indicator.pct_change = pct_change
    indicator.today_high = today_high
    indicator.today_low = today_low
    indicator.today_open = today_open
    indicator.today_volume = today_volume

    # DMAs
    indicator.dma_10 = dma_10
    indicator.dma_20 = dma_20
    indicator.dma_50 = dma_50
    indicator.dma_100 = dma_100
    indicator.dma_200 = dma_200
    indicator.dma_10_touch = dma_10_touch
    indicator.dma_20_touch = dma_20_touch
    indicator.dma_50_touch = dma_50_touch
    indicator.dma_100_touch = dma_100_touch
    indicator.dma_200_touch = dma_200_touch
    indicator.dma_10_signal = dma_10_signal
    indicator.dma_20_signal = dma_20_signal
    indicator.dma_50_signal = dma_50_signal
    indicator.dma_100_signal = dma_100_signal
    indicator.dma_200_signal = dma_200_signal

    # WMAs
    indicator.wma_5 = wma_5
    indicator.wma_10 = wma_10
    indicator.wma_20 = wma_20
    indicator.wma_30 = wma_30
    indicator.wma_5_touch = wma_5_touch
    indicator.wma_10_touch = wma_10_touch
    indicator.wma_20_touch = wma_20_touch
    indicator.wma_5_signal = wma_5_signal
    indicator.wma_10_signal = wma_10_signal
    indicator.wma_20_signal = wma_20_signal

    # 52W
    indicator.high_52w = metrics_52w["high_52w"]
    indicator.is_52w_high_intraday = metrics_52w["is_52w_high_intraday"]
    indicator.is_52w_closing_high = metrics_52w["is_52w_closing_high"]
    indicator.was_52w_high_yesterday = metrics_52w["was_52w_high_yesterday"]
    indicator.prev_52w_closing_high = metrics_52w["prev_52w_closing_high"]
    indicator.high_52w_date = metrics_52w["high_52w_date"]

    # Volume
    indicator.max_vol_21d = vol_metrics["max_vol_21d"]
    indicator.avg_vol_140d = vol_metrics["avg_vol_140d"]
    indicator.avg_vol_280d = vol_metrics["avg_vol_280d"]
    indicator.is_volume_breakout = vol_metrics["is_volume_breakout"]

    # Biweek/Week
    indicator.biweek_high = biweek["biweek_high"]
    indicator.biweek_vol = biweek["biweek_vol"]
    indicator.is_biweek_bo = biweek["is_biweek_bo"]
    indicator.week_high = week_bo["week_high"]
    indicator.week_vol = week_bo["week_vol"]
    indicator.is_week_bo = week_bo["is_week_bo"]

    # Gap
    indicator.gap_pct = gap["gap_pct"]
    indicator.is_gap_up = gap["is_gap_up"]
    indicator.is_gap_down = gap["is_gap_down"]

    # 90D
    indicator.high_90d = extremes_90d["high_90d"]
    indicator.low_90d = extremes_90d["low_90d"]
    indicator.is_90d_high = extremes_90d["is_90d_high"]
    indicator.is_90d_low_touch = extremes_90d["is_90d_low_touch"]

    # Result proximity
    indicator.days_to_result = result_prox["days_to_result"]
    indicator.result_within_7d = result_prox["result_within_7d"]
    indicator.result_within_10d = result_prox["result_within_10d"]
    indicator.result_within_15d = result_prox["result_within_15d"]
    indicator.result_declared_10d = result_prox["result_declared_10d"]

    return indicator
