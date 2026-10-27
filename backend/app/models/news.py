from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(120))
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    sentiment: Mapped[str | None] = mapped_column(String(16), nullable=True)  # V2
    hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    currency_links: Mapped[list["NewsCurrency"]] = relationship(
        back_populates="news", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def currencies(self) -> list[str]:
        return sorted(link.currency for link in self.currency_links)


class NewsCurrency(Base):
    """Devises / actifs associés à une news (colonne "currencies" du plan)."""

    __tablename__ = "news_currencies"

    news_id: Mapped[int] = mapped_column(ForeignKey("news.id", ondelete="CASCADE"), primary_key=True)
    currency: Mapped[str] = mapped_column(String(12), primary_key=True, index=True)

    news: Mapped[News] = relationship(back_populates="currency_links")
