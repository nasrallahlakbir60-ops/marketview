"""Tâche news (toutes les 60 s) : fetch -> filtre -> dédup -> enregistrement -> publication Redis Pub/Sub."""

import asyncio
import json

import httpx

from app.config import get_settings
from app.core.logging import get_logger
from app.database import SessionLocal
from app.models import News
from app.providers.base import NewsProvider, ProviderError, RawNews
from app.providers.finnhub import FinnhubNewsProvider, FinnhubNotAvailable
from app.providers.rss import rss_providers
from app.redis_client import NEWS_CHANNEL
from app.schemas.news import NewsOut
from app.services import cache, sources
from app.services.news_store import save_news

logger = get_logger(__name__)
LOCK_KEY = "lock:fetch_news"
_warned_missing: set[str] = set()


def build_providers() -> list[NewsProvider]:
    settings = get_settings()
    providers: list[NewsProvider] = [*rss_providers(), FinnhubNewsProvider(settings.finnhub_api_key)]
    active = []
    for provider in providers:
        if provider.is_configured():
            active.append(provider)
        elif provider.name not in _warned_missing:
            logger.warning("%s : clé API absente, source ignorée.", provider.name)
            _warned_missing.add(provider.name)
    return active


async def collect(providers: list[NewsProvider], client: httpx.AsyncClient) -> list[RawNews]:
    results = await asyncio.gather(*(provider.fetch(client) for provider in providers), return_exceptions=True)
    items: list[RawNews] = []
    for provider, result in zip(providers, results, strict=True):
        if isinstance(result, BaseException):
            level = logger.warning if isinstance(result, (ProviderError, httpx.HTTPError)) else logger.error
            level("Échec de la source %s : %s", provider.name, result)
            if provider.name == "Finnhub":
                message = (
                    "Accès refusé par Finnhub (clé invalide ou offre insuffisante)"
                    if isinstance(result, FinnhubNotAvailable)
                    else "Source momentanément indisponible"
                )
                sources.record_error("Finnhub", message)
            continue
        if provider.name == "Finnhub":
            sources.clear_error("Finnhub")
        items.extend(result)
    return items


def store_and_publish(items: list[RawNews]) -> list[News]:
    with SessionLocal() as db:
        created = save_news(db, items)
        payloads = [NewsOut.from_model(news).model_dump(mode="json") for news in created]
    if created:
        cache.delete_pattern("news:*")
        for payload in payloads:
            cache.publish(NEWS_CHANNEL, json.dumps(payload))
    return created


async def run_fetch_news(client: httpx.AsyncClient | None = None) -> int:
    """Exécute un cycle complet. Renvoie le nombre de news nouvelles."""
    settings = get_settings()
    if not cache.acquire_lock(LOCK_KEY, max(settings.news_fetch_interval_seconds - 5, 10)):
        return 0
    providers = build_providers()
    if client is None:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as own_client:
            items = await collect(providers, own_client)
    else:
        items = await collect(providers, client)
    created = await asyncio.to_thread(store_and_publish, items)
    logger.info("News : %d récupérées, %d nouvelles.", len(items), len(created))
    return len(created)


if __name__ == "__main__":
    from app.core.logging import setup_logging

    setup_logging(get_settings().log_level)
    asyncio.run(run_fetch_news())
