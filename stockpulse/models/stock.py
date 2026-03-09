from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockpulse.models.base import Base, TimestampMixin


class Stock(Base, TimestampMixin):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    nse_symbol: Mapped[str | None] = mapped_column(String(20), unique=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100))
    industry: Mapped[str | None] = mapped_column(String(100))
    isin: Mapped[str | None] = mapped_column(String(12))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    daily_prices = relationship("DailyPrice", back_populates="stock", lazy="dynamic")
    weekly_prices = relationship("WeeklyPrice", back_populates="stock", lazy="dynamic")
    indicators = relationship(
        "StockIndicator", back_populates="stock", lazy="dynamic"
    )
    color_classifications = relationship(
        "ColorClassification", back_populates="stock", lazy="dynamic"
    )
    notes = relationship("Note", back_populates="stock", lazy="dynamic")
    events = relationship("Event", back_populates="stock", lazy="dynamic")

    __table_args__ = (
        Index("ix_stocks_is_active", "is_active", postgresql_where=(is_active == True)),
    )

    def __repr__(self) -> str:
        return f"<Stock {self.symbol} ({self.company_name})>"
