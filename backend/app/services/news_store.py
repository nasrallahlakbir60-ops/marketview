"""Enregistrement des news : attribution des devises, déduplication, insertion en base."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import News, NewsCurrency
from app.providers.base import RawNews
from app.services.dedup import dedup
from app.services.news_filter import tag_news


def save_news(db: Session, items: list[RawNews]) -> list[News]:
    """Insère les news inédites qui concernent au moins une devise / un actif. Renvoie les news créées."""
    candidates = []
    for digest, item in dedup(items):
        tags = tag_news(item.title, item.summary, item.default_tags)
        if tags:
            candidates.append((digest, item, tags))
    if not candidates:
        return []

    hashes = [digest for digest, _, _ in candidates]
    existing = set(db.scalars(select(News.hash).where(News.hash.in_(hashes))))

    created: list[News] = []
    for digest, item, tags in candidates:
        if digest in existing:
            continue
        news = News(
            title=item.title[:1000],
            summary=item.summary,
            url=item.url,
            source=item.source[:120],
            image_url=item.image_url,
            published_at=item.published_at,
            hash=digest,
            currency_links=[NewsCurrency(currency=tag) for tag in tags],
        )
        db.add(news)
        created.append(news)
    db.commit()
    created.sort(key=lambda news: news.published_at)
    return created
