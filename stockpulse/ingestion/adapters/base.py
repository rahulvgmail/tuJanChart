"""Abstract base class for data source adapters.

Implementing a new data source (e.g., Zerodha Kite) requires only
subclassing DataAdapter and implementing these methods.
"""

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class DataAdapter(ABC):
    """Interface for market data providers."""

    @abstractmethod
    def fetch_daily_ohlcv(
        self, symbols: list[str], start: date, end: date
    ) -> dict[str, pd.DataFrame]:
        """Fetch daily OHLCV data for a list of symbols.

        Args:
            symbols: List of NSE/BSE ticker symbols.
            start: Start date (inclusive).
            end: End date (inclusive).

        Returns:
            Dict mapping symbol -> DataFrame with columns:
            [date, open, high, low, close, volume]
        """
        ...

    @abstractmethod
    def fetch_quotes(self, symbols: list[str]) -> dict[str, dict]:
        """Fetch current quotes (intraday snapshot) for symbols.

        Returns:
            Dict mapping symbol -> {
                'open': float, 'high': float, 'low': float,
                'close': float, 'volume': int, 'prev_close': float,
                'pe': float | None, 'market_cap': float | None
            }
        """
        ...

    @abstractmethod
    def fetch_board_meetings(
        self, from_date: date, to_date: date
    ) -> list[dict]:
        """Fetch board meeting announcements.

        Returns:
            List of dicts: {
                'security_code': str, 'company_name': str,
                'purpose': str, 'meeting_date': date,
                'announcement_date': date
            }
        """
        ...
