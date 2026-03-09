"""Celery tasks for data ingestion."""

import logging
from datetime import date, timedelta

from stockpulse.extensions import celery_app, get_db
from stockpulse.ingestion.adapters.yfinance_adapter import YFinanceAdapter
from stockpulse.ingestion.adapters.bse_adapter import BSEAdapter
from stockpulse.models.price import DailyPrice, WeeklyPrice
from stockpulse.models.stock import Stock
from stockpulse.models.corporate_action import BoardMeeting, ResultDate
from stockpulse.utils.market_calendar import is_trading_day, prev_trading_day

logger = logging.getLogger(__name__)


def _get_adapter():
    """Get the configured data adapter."""
    # Future: read from config to switch adapters
    return YFinanceAdapter()


def _get_active_symbols(session) -> list[tuple[int, str]]:
    """Return list of (stock_id, nse_symbol) for all active stocks."""
    stocks = (
        session.query(Stock.id, Stock.nse_symbol)
        .filter(Stock.is_active == True, Stock.nse_symbol.isnot(None))
        .all()
    )
    return [(s.id, s.nse_symbol) for s in stocks]


def _upsert_daily_prices(session, stock_id: int, df) -> int:
    """Upsert daily price rows. Returns count of rows written."""
    count = 0
    for _, row in df.iterrows():
        existing = (
            session.query(DailyPrice)
            .filter(DailyPrice.stock_id == stock_id, DailyPrice.date == row["date"])
            .first()
        )
        if existing:
            existing.open = row["open"]
            existing.high = row["high"]
            existing.low = row["low"]
            existing.close = row["close"]
            existing.volume = int(row["volume"]) if row["volume"] else None
        else:
            session.add(
                DailyPrice(
                    stock_id=stock_id,
                    date=row["date"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=int(row["volume"]) if row["volume"] else None,
                )
            )
        count += 1
    return count


def _generate_weekly_prices(session, stock_id: int, start: date, end: date) -> int:
    """Aggregate daily prices into weekly prices (Friday close).
    Returns count of weekly rows upserted."""
    from sqlalchemy import func

    daily_rows = (
        session.query(DailyPrice)
        .filter(
            DailyPrice.stock_id == stock_id,
            DailyPrice.date >= start,
            DailyPrice.date <= end,
        )
        .order_by(DailyPrice.date)
        .all()
    )

    if not daily_rows:
        return 0

    # Group by ISO week
    weeks: dict[tuple[int, int], list[DailyPrice]] = {}
    for dp in daily_rows:
        iso = dp.date.isocalendar()
        key = (iso.year, iso.week)
        weeks.setdefault(key, []).append(dp)

    count = 0
    for (yr, wk), days in weeks.items():
        days.sort(key=lambda d: d.date)
        last_day = days[-1]
        week_ending = last_day.date

        week_open = days[0].open
        week_high = max(d.high for d in days if d.high is not None) if any(d.high for d in days) else None
        week_low = min(d.low for d in days if d.low is not None) if any(d.low for d in days) else None
        week_close = last_day.close
        week_volume = sum(d.volume for d in days if d.volume is not None)

        existing = (
            session.query(WeeklyPrice)
            .filter(
                WeeklyPrice.stock_id == stock_id,
                WeeklyPrice.week_ending == week_ending,
            )
            .first()
        )
        if existing:
            existing.open = week_open
            existing.high = week_high
            existing.low = week_low
            existing.close = week_close
            existing.volume = week_volume
        else:
            session.add(
                WeeklyPrice(
                    stock_id=stock_id,
                    week_ending=week_ending,
                    open=week_open,
                    high=week_high,
                    low=week_low,
                    close=week_close,
                    volume=week_volume,
                )
            )
        count += 1

    return count


@celery_app.task(name="ingestion.pull_eod_data", bind=True, max_retries=3)
def pull_eod_data(self):
    """Pull end-of-day OHLCV data for all active stocks.

    Scheduled daily at 4:00 PM IST via Celery Beat.
    """
    today = date.today()
    if not is_trading_day(today):
        logger.info("Not a trading day (%s), skipping EOD pull", today)
        return {"status": "skipped", "reason": "not_trading_day"}

    adapter = _get_adapter()
    session = get_db()

    try:
        stocks = _get_active_symbols(session)
        if not stocks:
            logger.warning("No active stocks found")
            return {"status": "no_stocks"}

        symbol_to_id = {sym: sid for sid, sym in stocks}
        symbols = list(symbol_to_id.keys())

        # Fetch last 5 trading days to catch any missed data
        start = today - timedelta(days=7)
        data = adapter.fetch_daily_ohlcv(symbols, start, today)

        total_rows = 0
        for sym, df in data.items():
            stock_id = symbol_to_id.get(sym)
            if stock_id and not df.empty:
                rows = _upsert_daily_prices(session, stock_id, df)
                total_rows += rows
                # Generate weekly prices for this period
                _generate_weekly_prices(session, stock_id, start, today)

        session.commit()
        logger.info("EOD pull complete: %d rows for %d stocks", total_rows, len(data))

        # Chain: trigger indicator recomputation
        from stockpulse.engine.tasks import recompute_universe
        recompute_universe.delay(today.isoformat())

        return {"status": "ok", "stocks": len(data), "rows": total_rows}

    except Exception as exc:
        session.rollback()
        logger.exception("EOD pull failed")
        raise self.retry(exc=exc, countdown=60)
    finally:
        session.close()


@celery_app.task(name="ingestion.pull_intraday_quotes", bind=True)
def pull_intraday_quotes(self):
    """Pull current quotes for all active stocks during market hours.

    Scheduled every 3 minutes during 9:15 AM - 3:30 PM IST.
    """
    from stockpulse.utils.market_calendar import is_market_open

    if not is_market_open():
        return {"status": "skipped", "reason": "market_closed"}

    today = date.today()
    adapter = _get_adapter()
    session = get_db()

    try:
        stocks = _get_active_symbols(session)
        if not stocks:
            return {"status": "no_stocks"}

        symbol_to_id = {sym: sid for sid, sym in stocks}
        symbols = list(symbol_to_id.keys())

        quotes = adapter.fetch_quotes(symbols)

        updated = 0
        for sym, quote in quotes.items():
            stock_id = symbol_to_id.get(sym)
            if not stock_id or quote.get("close") is None:
                continue

            existing = (
                session.query(DailyPrice)
                .filter(DailyPrice.stock_id == stock_id, DailyPrice.date == today)
                .first()
            )
            if existing:
                existing.open = quote.get("open") or existing.open
                existing.high = quote.get("high") or existing.high
                existing.low = quote.get("low") or existing.low
                existing.close = quote["close"]
                existing.volume = quote.get("volume") or existing.volume
            else:
                session.add(
                    DailyPrice(
                        stock_id=stock_id,
                        date=today,
                        open=quote.get("open"),
                        high=quote.get("high"),
                        low=quote.get("low"),
                        close=quote["close"],
                        volume=quote.get("volume"),
                    )
                )
            updated += 1

        session.commit()
        logger.info("Intraday update: %d stocks", updated)
        return {"status": "ok", "updated": updated}

    except Exception:
        session.rollback()
        logger.exception("Intraday pull failed")
        return {"status": "error"}
    finally:
        session.close()


@celery_app.task(name="ingestion.backfill_stock", bind=True, max_retries=3)
def backfill_stock(self, stock_id: int, days: int = 365):
    """Backfill historical daily prices for a single stock.

    Called when a new stock is added to the universe.
    """
    adapter = _get_adapter()
    session = get_db()

    try:
        stock = session.query(Stock).filter(Stock.id == stock_id).first()
        if not stock or not stock.nse_symbol:
            logger.warning("Stock %d not found or has no NSE symbol", stock_id)
            return {"status": "not_found"}

        end = date.today()
        start = end - timedelta(days=days)

        data = adapter.fetch_daily_ohlcv([stock.nse_symbol], start, end)
        df = data.get(stock.nse_symbol)

        if df is None or df.empty:
            logger.warning("No historical data for %s", stock.nse_symbol)
            return {"status": "no_data", "symbol": stock.nse_symbol}

        rows = _upsert_daily_prices(session, stock_id, df)
        weekly = _generate_weekly_prices(session, stock_id, start, end)
        session.commit()

        logger.info(
            "Backfilled %s: %d daily rows, %d weekly rows",
            stock.nse_symbol,
            rows,
            weekly,
        )
        return {
            "status": "ok",
            "symbol": stock.nse_symbol,
            "daily_rows": rows,
            "weekly_rows": weekly,
        }

    except Exception as exc:
        session.rollback()
        logger.exception("Backfill failed for stock %d", stock_id)
        raise self.retry(exc=exc, countdown=120)
    finally:
        session.close()


@celery_app.task(name="ingestion.pull_corporate_actions", bind=True)
def pull_corporate_actions(self):
    """Pull board meeting and result date data from BSE.

    Scheduled daily at 6:00 PM IST.
    """
    bse = BSEAdapter()
    session = get_db()

    try:
        today = date.today()
        # Look ahead 90 days for upcoming board meetings
        meetings = bse.fetch_board_meetings(today, today + timedelta(days=90))

        if not meetings:
            logger.info("No new board meetings found")
            return {"status": "ok", "meetings": 0}

        added = 0
        for m in meetings:
            # Find matching stock by BSE security code
            stock = (
                session.query(Stock)
                .filter(Stock.symbol == m["security_code"])
                .first()
            )
            if not stock:
                continue

            # Check if this meeting already exists
            existing = (
                session.query(BoardMeeting)
                .filter(
                    BoardMeeting.stock_id == stock.id,
                    BoardMeeting.meeting_date == m["meeting_date"],
                )
                .first()
            )
            if not existing:
                session.add(
                    BoardMeeting(
                        stock_id=stock.id,
                        purpose=m["purpose"],
                        meeting_date=m["meeting_date"],
                        announcement_date=m.get("announcement_date"),
                    )
                )
                added += 1

                # If purpose is related to results, update result_dates
                purpose = (m.get("purpose") or "").lower()
                if "result" in purpose or "financial" in purpose:
                    _upsert_result_date(session, stock.id, m["meeting_date"])

        session.commit()
        logger.info("Corporate actions: %d new meetings added", added)
        return {"status": "ok", "meetings": added}

    except Exception:
        session.rollback()
        logger.exception("Corporate actions pull failed")
        return {"status": "error"}
    finally:
        session.close()


def _upsert_result_date(session, stock_id: int, result_date: date):
    """Create or update the result date for the current quarter."""
    # Determine quarter from the meeting date
    month = result_date.month
    year = result_date.year
    if month <= 3:
        quarter = f"Q4FY{year}"
    elif month <= 6:
        quarter = f"Q1FY{year + 1}"
    elif month <= 9:
        quarter = f"Q2FY{year + 1}"
    else:
        quarter = f"Q3FY{year + 1}"

    existing = (
        session.query(ResultDate)
        .filter(ResultDate.stock_id == stock_id, ResultDate.quarter == quarter)
        .first()
    )
    if existing:
        existing.result_date = result_date
    else:
        session.add(
            ResultDate(
                stock_id=stock_id,
                quarter=quarter,
                result_date=result_date,
                source="bse",
            )
        )
