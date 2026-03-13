"""Shared pytest fixtures for StockPulse tests."""

import os
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://stockpulse:stockpulse@localhost:5432/stockpulse_test",
)

from stockpulse.models.base import Base


@pytest.fixture(scope="session")
def db_engine():
    """Create tables once for the whole test session."""
    engine = create_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    """Per-test session wrapped in a transaction that rolls back."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def sample_stock(db_session):
    """A single active stock."""
    from stockpulse.models.stock import Stock

    stock = Stock(
        symbol="500325",
        nse_symbol="RELIANCE",
        company_name="Reliance Industries Ltd",
        sector="Oil & Gas",
        industry="Refineries",
        is_active=True,
    )
    db_session.add(stock)
    db_session.flush()
    return stock


@pytest.fixture()
def second_stock(db_session):
    """A second stock for multi-stock tests."""
    from stockpulse.models.stock import Stock

    stock = Stock(
        symbol="500180",
        nse_symbol="HDFCBANK",
        company_name="HDFC Bank Ltd",
        sector="Banking",
        industry="Private Bank",
        is_active=True,
    )
    db_session.add(stock)
    db_session.flush()
    return stock


@pytest.fixture()
def sample_prices(db_session, sample_stock):
    """22 trading days of price data for sample_stock."""
    from stockpulse.models.price import DailyPrice

    base_date = date(2026, 3, 11)
    prices = []
    day_offset = 0

    for i in range(30):
        d = base_date - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        price = Decimal("1200.00") + Decimal(str((day_offset - 10) * 3))
        dp = DailyPrice(
            stock_id=sample_stock.id,
            date=d,
            open=price - Decimal("5"),
            high=price + Decimal("15"),
            low=price - Decimal("12"),
            close=price,
            volume=1_000_000 + day_offset * 50_000,
        )
        db_session.add(dp)
        prices.append(dp)
        day_offset += 1

    db_session.flush()
    return prices


def _make_indicator(db_session, stock_id, as_of, **overrides):
    """Helper to create a StockIndicator with sensible defaults."""
    from stockpulse.models.indicator import StockIndicator

    defaults = dict(
        stock_id=stock_id,
        date=as_of,
        current_price=Decimal("1200.00"),
        prev_close=Decimal("1190.00"),
        pct_change=Decimal("0.84"),
        today_high=Decimal("1215.00"),
        today_low=Decimal("1185.00"),
        today_open=Decimal("1195.00"),
        today_volume=1_500_000,
        dma_10=Decimal("1195.00"),
        dma_20=Decimal("1180.00"),
        dma_50=Decimal("1150.00"),
        # All boolean fields must be set (NOT NULL in DB)
        dma_10_touch=False,
        dma_20_touch=False,
        dma_50_touch=False,
        dma_100_touch=False,
        dma_200_touch=False,
        wma_5_touch=False,
        wma_10_touch=False,
        wma_20_touch=False,
        is_52w_closing_high=False,
        is_52w_high_intraday=False,
        was_52w_high_yesterday=False,
        is_volume_breakout=False,
        is_biweek_bo=False,
        is_week_bo=False,
        is_gap_up=False,
        is_gap_down=False,
        is_90d_high=False,
        is_90d_low_touch=False,
        result_within_7d=False,
        result_within_10d=False,
        result_within_15d=False,
        result_declared_10d=False,
    )
    defaults.update(overrides)

    ind = StockIndicator(**defaults)
    db_session.add(ind)
    db_session.flush()
    return ind
