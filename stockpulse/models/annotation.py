from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockpulse.models.base import Base


class ColorClassification(Base):
    __tablename__ = "color_classifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    color: Mapped[str] = mapped_column(String(10), nullable=False)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    comment: Mapped[str | None] = mapped_column(Text)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    stock = relationship("Stock", back_populates="color_classifications")

    __table_args__ = (
        Index(
            "ix_color_current",
            "stock_id",
            postgresql_where=(is_current == True),
        ),
    )

    def __repr__(self) -> str:
        return f"<Color {self.stock_id} {self.color}>"


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), nullable=False)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    author_type: Mapped[str] = mapped_column(String(10), default="human")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    stock = relationship("Stock", back_populates="notes")

    __table_args__ = (
        Index("ix_notes_stock_created", "stock_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Note {self.stock_id} by {self.author_type}>"


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    before_value: Mapped[dict | None] = mapped_column(JSONB)
    after_value: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} {self.entity_type}:{self.entity_id}>"
