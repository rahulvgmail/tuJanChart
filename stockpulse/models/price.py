from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockpulse.models.base import Base


class DailyPrice(Base):
    __tablename__ = "daily_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float | None] = mapped_column(Numeric(12, 2))
    high: Mapped[float | None] = mapped_column(Numeric(12, 2))
    low: Mapped[float | None] = mapped_column(Numeric(12, 2))
    close: Mapped[float | None] = mapped_column(Numeric(12, 2))
    volume: Mapped[int | None] = mapped_column(BigInteger)

    stock = relationship("Stock", back_populates="daily_prices")

    __table_args__ = (
        Index("ix_daily_prices_stock_date", "stock_id", "date", unique=True),
        Index("ix_daily_prices_date_desc", "stock_id", date.desc()),
    )

    def __repr__(self) -> str:
        return f"<DailyPrice {self.stock_id} {self.date} C={self.close}>"


class WeeklyPrice(Base):
    __tablename__ = "weekly_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    week_ending: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float | None] = mapped_column(Numeric(12, 2))
    high: Mapped[float | None] = mapped_column(Numeric(12, 2))
    low: Mapped[float | None] = mapped_column(Numeric(12, 2))
    close: Mapped[float | None] = mapped_column(Numeric(12, 2))
    volume: Mapped[int | None] = mapped_column(BigInteger)

    stock = relationship("Stock", back_populates="weekly_prices")

    __table_args__ = (
        Index(
            "ix_weekly_prices_stock_week", "stock_id", "week_ending", unique=True
        ),
    )

    def __repr__(self) -> str:
        return f"<WeeklyPrice {self.stock_id} {self.week_ending} C={self.close}>"
