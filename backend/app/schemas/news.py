from datetime import datetime

from pydantic import BaseModel

from app.models import News
from app.schemas.common import as_utc


class NewsOut(BaseModel):
    id: int
    title: str
    summary: str | None
    url: str
    source: str
    image_url: str | None
    published_at: datetime
    currencies: list[str]

    @classmethod
    def from_model(cls, news: News) -> "NewsOut":
        return cls(
            id=news.id,
            title=news.title,
            summary=news.summary,
            url=news.url,
            source=news.source,
            image_url=news.image_url,
            published_at=as_utc(news.published_at),
            currencies=news.currencies,
        )


class SourceStatus(BaseModel):
    name: str
    configured: bool
    message: str | None = None
