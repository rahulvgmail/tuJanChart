"""Indian stock market calendar utilities."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)

# NSE holidays for 2026 (update annually)
NSE_HOLIDAYS_2026 = {
    date(2026, 1, 26),  # Republic Day
    date(2026, 2, 17),  # Maha Shivaratri
    date(2026, 3, 10),  # Holi
    date(2026, 3, 30),  # Id-Ul-Fitr (Tentative)
    date(2026, 4, 2),   # Ram Navami
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 14),  # Dr. Ambedkar Jayanti
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 6, 6),   # Id-Ul-Adha (Bakri Id) (Tentative)
    date(2026, 7, 6),   # Muharram (Tentative)
    date(2026, 8, 15),  # Independence Day
    date(2026, 9, 4),   # Milad-Un-Nabi (Tentative)
    date(2026, 10, 2),  # Mahatma Gandhi Jayanti
    date(2026, 10, 20), # Dussehra
    date(2026, 11, 9),  # Diwali (Laxmi Pujan)
    date(2026, 11, 10), # Diwali Balipratipada
    date(2026, 11, 27), # Gurunanak Jayanti
    date(2026, 12, 25), # Christmas
}


def is_trading_day(d: date) -> bool:
    """Check if a date is a trading day (not weekend, not holiday)."""
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return d not in NSE_HOLIDAYS_2026


def is_market_open() -> bool:
    """Check if the market is currently open."""
    now = datetime.now(IST)
    if not is_trading_day(now.date()):
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE


def next_trading_day(d: date) -> date:
    """Get the next trading day after the given date."""
    candidate = d + timedelta(days=1)
    while not is_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def prev_trading_day(d: date) -> date:
    """Get the previous trading day before the given date."""
    candidate = d - timedelta(days=1)
    while not is_trading_day(candidate):
        candidate -= timedelta(days=1)
    return candidate


def trading_days_between(start: date, end: date) -> list[date]:
    """Get all trading days between start and end (inclusive)."""
    days = []
    current = start
    while current <= end:
        if is_trading_day(current):
            days.append(current)
        current += timedelta(days=1)
    return days


def last_n_trading_days(d: date, n: int) -> list[date]:
    """Get the last n trading days ending on (and including) date d."""
    days = []
    current = d
    while len(days) < n:
        if is_trading_day(current):
            days.append(current)
        current -= timedelta(days=1)
    return list(reversed(days))
