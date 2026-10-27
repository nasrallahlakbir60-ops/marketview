from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.pairs import get_pair_or_404
from app.config import get_settings
from app.core.rate_limit import rate_limit
from app.database import get_db
from app.models import News, NewsCurrency
from app.schemas.news import NewsOut, SourceStatus
from app.services import cache, pair_mapping, sources
from app.services.serverless import ensure_database, refresh_if_stale

router = APIRouter(prefix="/api/news", tags=["news"], dependencies=[Depends(rate_limit), Depends(ensure_database)])


def news_cache_key(symbol: str, limit: int) -> str:
    return f"news:{symbol}:{limit}"


@router.get("", response_model=list[NewsOut], dependencies=[Depends(refresh_if_stale("news"))])
def list_news(
    pair: str = Query(..., description="Symbole de la paire, ex : EURUSD"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[NewsOut] | list[dict]:
    """News des devises / actifs de la paire, les plus récentes d'abord (lecture BDD + cache Redis 60 s)."""
    pair_row = get_pair_or_404(db, pair)
    key = news_cache_key(pair_row.symbol, limit)
    cached = cache.get_json(key)
    if cached is not None:
        return cached

    tags = pair_mapping.news_tags(pair_row.base_currency, pair_row.quote_currency, pair_row.category)
    matching_ids = select(NewsCurrency.news_id).where(NewsCurrency.currency.in_(tags))
    rows = db.scalars(
        select(News).where(News.id.in_(matching_ids)).order_by(News.published_at.desc(), News.id.desc()).limit(limit)
    )
    result = [NewsOut.from_model(news) for news in rows]
    cache.set_json(key, [item.model_dump(mode="json") for item in result], cache.NEWS_TTL)
    return result


@router.get("/sources", response_model=list[SourceStatus])
def news_sources() -> list[SourceStatus]:
    settings = get_settings()
    return [
        sources.status("Flux RSS", True),
        sources.status("Finnhub", bool(settings.finnhub_api_key), "FINNHUB_API_KEY"),
    ]
