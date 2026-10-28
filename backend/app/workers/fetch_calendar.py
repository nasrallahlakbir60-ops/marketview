"""Tâche calendrier économique (toutes les heures).

Finnhub est utilisé si FINNHUB_API_KEY est fournie et que l'offre inclut le calendrier ;
sinon (pas de clé, accès refusé, panne), repli sur le flux public ForexFactory, sans clé.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import delete, select

from app.config import get_settings
from app.core.logging import get_logger
from app.database import SessionLocal
from app.models import EconomicEvent
from app.providers.base import ProviderError
from app.providers.finnhub import FinnhubNotAvailable, fetch_economic_calendar
from app.providers.forexfactory import fetch_week_calendar
from app.services import cache, pair_mapping, sources

logger = get_logger(__name__)
LOCK_KEY = "lock:fetch_calendar"
SOURCE_NAME = "Calendrier économique"
ACTIVE_SOURCE_KEY = "source:calendar:active"
DEFAULT_SOURCE = "ForexFactory"
DAYS_BEFORE = 1
DAYS_AFTER = 7
KEEP_DAYS = 14


def active_source() -> str:
    """Nom de la dernière source qui a alimenté le calendrier."""
    name = cache.get_json(ACTIVE_SOURCE_KEY)
    return name if isinstance(name, str) else DEFAULT_SOURCE


def save_events(events: list[dict], source: str) -> int:
    """Enregistre les événements ; chacun porte soit un code pays (Finnhub), soit une devise (ForexFactory)."""
    mapping = pair_mapping.country_to_currency()
    saved = 0
    with SessionLocal() as db:
        for event in events:
            event = dict(event)
            if "currency" in event:
                currency = event["currency"]
                country = pair_mapping.country_of(currency)
            else:
                country = pair_mapping.normalize_country(event["country"])
                currency = mapping.get(country)
            if currency is None or country is None:
                continue  # pays / devise sans paire suivie
            existing = db.scalar(
                select(EconomicEvent).where(
                    EconomicEvent.country == country,
                    EconomicEvent.event_name == event["event_name"],
                    EconomicEvent.event_time == event["event_time"],
                )
            )
            values = {**event, "country": country, "currency": currency, "source": source}
            if existing is None:
                db.add(EconomicEvent(**values))
            else:
                for key, value in values.items():
                    setattr(existing, key, value)
            saved += 1
        cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)
        db.execute(delete(EconomicEvent).where(EconomicEvent.event_time < cutoff))
        db.commit()
    return saved


async def _fetch(client: httpx.AsyncClient, api_key: str) -> tuple[list[dict], str]:
    if api_key:
        today = datetime.now(timezone.utc).date()
        try:
            events = await fetch_economic_calendar(client, api_key, today - timedelta(days=DAYS_BEFORE), today + timedelta(days=DAYS_AFTER))
            return events, "Finnhub"
        except FinnhubNotAvailable as exc:
            logger.info("Calendrier Finnhub non inclus dans l'offre (%s) : repli sur ForexFactory.", exc)
        except ProviderError as exc:
            logger.warning("Calendrier Finnhub en échec (%s) : repli sur ForexFactory.", exc)
    return await fetch_week_calendar(client), DEFAULT_SOURCE


async def run_fetch_calendar(client: httpx.AsyncClient | None = None) -> int:
    settings = get_settings()
    if not cache.acquire_lock(LOCK_KEY, 55 * 60):
        return 0

    try:
        if client is None:
            async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as own_client:
                events, source = await _fetch(own_client, settings.finnhub_api_key)
        else:
            events, source = await _fetch(client, settings.finnhub_api_key)
    except ProviderError as exc:
        logger.warning("Calendrier en échec : %s", exc)
        sources.record_error(SOURCE_NAME, "Source momentanément indisponible")
        cache.release_lock(LOCK_KEY)
        return 0

    sources.clear_error(SOURCE_NAME)
    count = await asyncio.to_thread(save_events, events, source)
    cache.set_json(ACTIVE_SOURCE_KEY, source, 7 * 24 * 3600)
    cache.delete_pattern("calendar:*")
    logger.info("Calendrier (%s) : %d événements enregistrés.", source, count)
    return count


if __name__ == "__main__":
    from app.core.logging import setup_logging

    setup_logging(get_settings().log_level)
    asyncio.run(run_fetch_calendar())
