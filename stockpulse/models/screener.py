from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockpulse.models.base import Base, TimestampMixin


class Screener(Base, TimestampMixin):
    __tablename__ = "screeners"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    conditions = relationship(
        "ScreenerCondition", back_populates="screener", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Screener {self.slug}>"


class ScreenerCondition(Base):
    __tablename__ = "screener_conditions"

    id: Mapped[int] = mapped_column(primary_key=True)
    screener_id: Mapped[int] = mapped_column(
        ForeignKey("screeners.id", ondelete="CASCADE"), nullable=False
    )
    field: Mapped[str] = mapped_column(String(50), nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[dict | None] = mapped_column(JSONB)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)

    screener = relationship("Screener", back_populates="conditions")

    def __repr__(self) -> str:
        return f"<ScreenerCondition {self.field} {self.operator} {self.value}>"


class ScreenerHistory(Base):
    __tablename__ = "screener_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    screener_id: Mapped[int] = mapped_column(
        ForeignKey("screeners.id"), nullable=False
    )
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    entered: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        Index("ix_screener_history_screener_date", "screener_id", "date"),
        Index(
            "ix_screener_history_stock_screener",
            "stock_id",
            "screener_id",
            "date",
        ),
    )
