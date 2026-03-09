"""yfinance-based data adapter for Indian equities."""

import logging
import time
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from stockpulse.ingestion.adapters.base import DataAdapter

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
BATCH_DELAY = 1.0  # seconds between batches to avoid rate limits


def _to_yf_symbol(symbol: str) -> str:
    """Convert NSE symbol to yfinance format (append .NS)."""
    if not symbol.endswith((".NS", ".BO")):
        return f"{symbol}.NS"
    return symbol


def _batched(items: list, size: int):
    """Yield successive chunks of `size` from `items`."""
    for i in range(0, len(items), size):
        yield items[i : i + size]


class YFinanceAdapter(DataAdapter):
    """Data adapter using yfinance (free, unofficial Yahoo Finance API)."""

    def fetch_daily_ohlcv(
        self, symbols: list[str], start: date, end: date
    ) -> dict[str, pd.DataFrame]:
        results = {}
        # yfinance end date is exclusive, so add 1 day
        end_str = (end + timedelta(days=1)).isoformat()
        start_str = start.isoformat()

        for batch_num, batch in enumerate(_batched(symbols, BATCH_SIZE)):
            yf_symbols = [_to_yf_symbol(s) for s in batch]
            ticker_str = " ".join(yf_symbols)

            try:
                logger.info(
                    "Fetching OHLCV batch %d (%d symbols)",
                    batch_num + 1,
                    len(batch),
                )
                data = yf.download(
                    ticker_str,
                    start=start_str,
                    end=end_str,
                    group_by="ticker",
                    auto_adjust=True,
                    threads=True,
                    progress=False,
                )

                if data.empty:
                    logger.warning("No data returned for batch %d", batch_num + 1)
                    continue

                for orig_sym, yf_sym in zip(batch, yf_symbols):
                    try:
                        # yfinance returns MultiIndex columns: (Ticker, Price) or (Price, Ticker)
                        # With group_by="ticker": (Ticker, Price)
                        # Without group_by or single: (Price, Ticker)
                        if isinstance(data.columns, pd.MultiIndex):
                            # Check if ticker is in first or second level
                            if yf_sym in data.columns.get_level_values(0):
                                ticker_data = data[yf_sym]
                            elif yf_sym in data.columns.get_level_values(1):
                                # Swap levels and select
                                ticker_data = data.swaplevel(axis=1)[yf_sym]
                            else:
                                logger.warning("No data for symbol %s", orig_sym)
                                continue
                        else:
                            ticker_data = data

                        if ticker_data.empty:
                            continue

                        # Handle both flat and MultiIndex column names
                        col_map = {}
                        for col in ticker_data.columns:
                            col_name = col[0] if isinstance(col, tuple) else col
                            col_map[col] = col_name

                        ticker_data = ticker_data.rename(columns=col_map)
                        df = ticker_data[["Open", "High", "Low", "Close", "Volume"]].copy()
                        df.columns = ["open", "high", "low", "close", "volume"]
                        df = df.dropna(subset=["close"])
                        df = df.reset_index()
                        # Handle index name (could be "Date" or "date")
                        date_col = [c for c in df.columns if str(c).lower() == "date"]
                        if date_col:
                            df = df.rename(columns={date_col[0]: "date"})
                        df["date"] = pd.to_datetime(df["date"]).dt.date
                        results[orig_sym] = df
                    except (KeyError, TypeError) as e:
                        logger.warning("No data for symbol %s: %s", orig_sym, e)

            except Exception:
                logger.exception("Error fetching batch %d", batch_num + 1)

            if batch_num < (len(symbols) // BATCH_SIZE):
                time.sleep(BATCH_DELAY)

        logger.info("Fetched OHLCV for %d/%d symbols", len(results), len(symbols))
        return results

    def fetch_quotes(self, symbols: list[str]) -> dict[str, dict]:
        results = {}

        for batch_num, batch in enumerate(_batched(symbols, BATCH_SIZE)):
            for sym in batch:
                try:
                    ticker = yf.Ticker(_to_yf_symbol(sym))
                    info = ticker.fast_info
                    results[sym] = {
                        "open": getattr(info, "open", None),
                        "high": getattr(info, "day_high", None),
                        "low": getattr(info, "day_low", None),
                        "close": getattr(info, "last_price", None),
                        "volume": getattr(info, "last_volume", None),
                        "prev_close": getattr(info, "previous_close", None),
                        "pe": None,  # yfinance fast_info doesn't reliably provide PE
                        "market_cap": getattr(info, "market_cap", None),
                    }
                except Exception:
                    logger.warning("Failed to fetch quote for %s", sym)

            if batch_num < (len(symbols) // BATCH_SIZE):
                time.sleep(BATCH_DELAY)

        logger.info("Fetched quotes for %d/%d symbols", len(results), len(symbols))
        return results

    def fetch_board_meetings(
        self, from_date: date, to_date: date
    ) -> list[dict]:
        # yfinance doesn't provide board meeting data.
        # This will be handled by the BSE adapter.
        logger.info("Board meeting fetch not supported by yfinance adapter")
        return []
