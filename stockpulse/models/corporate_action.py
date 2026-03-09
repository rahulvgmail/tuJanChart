from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from stockpulse.models.base import Base


class ResultDate(Base):
    __tablename__ = "result_dates"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    quarter: Mapped[str | None] = mapped_column(String(10))
    result_date: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_result_dates_stock_quarter", "stock_id", "quarter", unique=True),
        Index("ix_result_dates_date", "result_date"),
    )

    def __repr__(self) -> str:
        return f"<ResultDate {self.stock_id} {self.quarter} {self.result_date}>"


class BoardMeeting(Base):
    __tablename__ = "board_meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    purpose: Mapped[str | None] = mapped_column(Text)
    meeting_date: Mapped[date | None] = mapped_column(Date)
    announcement_date: Mapped[date | None] = mapped_column(Date)
    quarter: Mapped[str | None] = mapped_column(String(10))

    __table_args__ = (Index("ix_board_meetings_date", "meeting_date"),)

    def __repr__(self) -> str:
        return f"<BoardMeeting {self.stock_id} {self.meeting_date}>"


class ASMEntry(Base):
    __tablename__ = "asm_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    stage: Mapped[int | None] = mapped_column(Integer)
    isin: Mapped[str | None] = mapped_column(String(12))
    effective_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index(
            "ix_asm_current",
            "stock_id",
            postgresql_where=(is_current == True),
        ),
    )

    def __repr__(self) -> str:
        return f"<ASMEntry {self.stock_id} stage={self.stage}>"


class CircuitBand(Base):
    __tablename__ = "circuit_bands"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    series: Mapped[str | None] = mapped_column(String(10))
    band_pct: Mapped[float | None] = mapped_column(Integer)
    effective_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<CircuitBand {self.stock_id} {self.band_pct}%>"
