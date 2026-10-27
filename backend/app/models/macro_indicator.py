from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MacroIndicator(Base):
    __tablename__ = "macro_indicators"
    __table_args__ = (UniqueConstraint("country", "indicator", "source", name="uq_macro_country_indicator_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country: Mapped[str] = mapped_column(String(8), index=True)
    indicator: Mapped[str] = mapped_column(String(32))  # CPI, CORE_CPI, INTEREST_RATE...
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    previous: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast: Mapped[float | None] = mapped_column(Float, nullable=True)
    period: Mapped[str | None] = mapped_column(String(16), nullable=True)  # ex : 2026-09 ou 2025
    previous_period: Mapped[str | None] = mapped_column(String(16), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(16), nullable=True)  # monthly, annual, daily
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(String(64))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
