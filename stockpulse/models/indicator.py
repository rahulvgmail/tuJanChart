from datetime import date

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockpulse.models.base import Base


class StockIndicator(Base):
    __tablename__ = "stock_indicators"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Price data
    current_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    prev_close: Mapped[float | None] = mapped_column(Numeric(12, 2))
    pct_change: Mapped[float | None] = mapped_column(Numeric(8, 4))
    pe: Mapped[float | None] = mapped_column(Numeric(10, 2))
    market_cap_cr: Mapped[float | None] = mapped_column(Numeric(14, 2))
    today_high: Mapped[float | None] = mapped_column(Numeric(12, 2))
    today_low: Mapped[float | None] = mapped_column(Numeric(12, 2))
    today_open: Mapped[float | None] = mapped_column(Numeric(12, 2))
    today_volume: Mapped[int | None] = mapped_column(BigInteger)

    # Daily Moving Averages
    dma_10: Mapped[float | None] = mapped_column(Numeric(12, 4))
    dma_20: Mapped[float | None] = mapped_column(Numeric(12, 4))
    dma_50: Mapped[float | None] = mapped_column(Numeric(12, 4))
    dma_100: Mapped[float | None] = mapped_column(Numeric(12, 4))
    dma_200: Mapped[float | None] = mapped_column(Numeric(12, 4))

    # DMA Touch flags
    dma_10_touch: Mapped[bool] = mapped_column(Boolean, default=False)
    dma_20_touch: Mapped[bool] = mapped_column(Boolean, default=False)
    dma_50_touch: Mapped[bool] = mapped_column(Boolean, default=False)
    dma_100_touch: Mapped[bool] = mapped_column(Boolean, default=False)
    dma_200_touch: Mapped[bool] = mapped_column(Boolean, default=False)

    # DMA Signals: Hold, Reverse, or NULL
    dma_10_signal: Mapped[str | None] = mapped_column(String(10))
    dma_20_signal: Mapped[str | None] = mapped_column(String(10))
    dma_50_signal: Mapped[str | None] = mapped_column(String(10))
    dma_100_signal: Mapped[str | None] = mapped_column(String(10))
    dma_200_signal: Mapped[str | None] = mapped_column(String(10))

    # Weekly Moving Averages
    wma_5: Mapped[float | None] = mapped_column(Numeric(12, 4))
    wma_10: Mapped[float | None] = mapped_column(Numeric(12, 4))
    wma_20: Mapped[float | None] = mapped_column(Numeric(12, 4))
    wma_30: Mapped[float | None] = mapped_column(Numeric(12, 4))

    # WMA Touch and Signals
    wma_5_touch: Mapped[bool] = mapped_column(Boolean, default=False)
    wma_10_touch: Mapped[bool] = mapped_column(Boolean, default=False)
    wma_20_touch: Mapped[bool] = mapped_column(Boolean, default=False)
    wma_5_signal: Mapped[str | None] = mapped_column(String(10))
    wma_10_signal: Mapped[str | None] = mapped_column(String(10))
    wma_20_signal: Mapped[str | None] = mapped_column(String(10))

    # 52-Week metrics
    high_52w: Mapped[float | None] = mapped_column(Numeric(12, 2))
    is_52w_high_intraday: Mapped[bool] = mapped_column(Boolean, default=False)
    is_52w_closing_high: Mapped[bool] = mapped_column(Boolean, default=False)
    was_52w_high_yesterday: Mapped[bool] = mapped_column(Boolean, default=False)
    prev_52w_closing_high: Mapped[float | None] = mapped_column(Numeric(12, 2))
    high_52w_date: Mapped[date | None] = mapped_column(Date)

    # Volume analytics
    max_vol_21d: Mapped[int | None] = mapped_column(BigInteger)
    avg_vol_140d: Mapped[int | None] = mapped_column(BigInteger)
    avg_vol_280d: Mapped[int | None] = mapped_column(BigInteger)
    is_volume_breakout: Mapped[bool] = mapped_column(Boolean, default=False)

    # Biweekly / Weekly breakout
    biweek_high: Mapped[float | None] = mapped_column(Numeric(12, 2))
    biweek_vol: Mapped[int | None] = mapped_column(BigInteger)
    is_biweek_bo: Mapped[bool] = mapped_column(Boolean, default=False)
    week_high: Mapped[float | None] = mapped_column(Numeric(12, 2))
    week_vol: Mapped[int | None] = mapped_column(BigInteger)
    is_week_bo: Mapped[bool] = mapped_column(Boolean, default=False)

    # Gap
    gap_pct: Mapped[float | None] = mapped_column(Numeric(8, 4))
    is_gap_up: Mapped[bool] = mapped_column(Boolean, default=False)
    is_gap_down: Mapped[bool] = mapped_column(Boolean, default=False)

    # 90-day extremes
    high_90d: Mapped[float | None] = mapped_column(Numeric(12, 2))
    low_90d: Mapped[float | None] = mapped_column(Numeric(12, 2))
    is_90d_high: Mapped[bool] = mapped_column(Boolean, default=False)
    is_90d_low_touch: Mapped[bool] = mapped_column(Boolean, default=False)

    # Result date proximity
    days_to_result: Mapped[int | None] = mapped_column(Integer)
    result_within_7d: Mapped[bool] = mapped_column(Boolean, default=False)
    result_within_10d: Mapped[bool] = mapped_column(Boolean, default=False)
    result_within_15d: Mapped[bool] = mapped_column(Boolean, default=False)
    result_declared_10d: Mapped[bool] = mapped_column(Boolean, default=False)

    stock = relationship("Stock", back_populates="indicators")

    __table_args__ = (
        Index("ix_indicators_stock_date", "stock_id", "date", unique=True),
        Index("ix_indicators_date", "date"),
        Index(
            "ix_indicators_52w_closing",
            "date",
            postgresql_where=(is_52w_closing_high == True),
        ),
        Index(
            "ix_indicators_vol_breakout",
            "date",
            postgresql_where=(is_volume_breakout == True),
        ),
        Index(
            "ix_indicators_dma10_touch",
            "date",
            postgresql_where=(dma_10_touch == True),
        ),
    )

    def __repr__(self) -> str:
        return f"<StockIndicator {self.stock_id} {self.date} P={self.current_price}>"
