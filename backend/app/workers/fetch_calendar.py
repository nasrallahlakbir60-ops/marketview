"""Tâche calendrier économique (toutes les heures) via Finnhub, si FINNHUB_API_KEY est fournie."""

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
from app.services import cache, pair_mapping, sources

logger = get_logger(__name__)
LOCK_KEY = "lock:fetch_calendar"
SOURCE_NAME = "Finnhub (calendrier)"
DAYS_BEFORE = 1
DAYS_AFTER = 7
KEEP_DAYS = 14
_warned_missing = False


def save_events(events: list[dict]) -> int:
    mapping = pair_mapping.country_to_currency()
    saved = 0
    with SessionLocal() as db:
        for event in events:
            country = pair_mapping.normalize_country(event["country"])
            currency = mapping.get(country)
            if currency is None:
                continue  # pays sans paire suivie
            existing = db.scalar(
                select(EconomicEvent).where(
                    EconomicEvent.country == country,
                    EconomicEvent.event_name == event["event_name"],
                    EconomicEvent.event_time == event["event_time"],
                )
            )
            values = {**event, "country": country, "currency": currency, "source": "Finnhub"}
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


async def run_fetch_calendar(client: httpx.AsyncClient | None = None) -> int:
    global _warned_missing
    settings = get_settings()
    if not settings.finnhub_api_key:
        if not _warned_missing:
            logger.warning("FINNHUB_API_KEY absente : calendrier économique non disponible.")
            _warned_missing = True
        return 0
    if not cache.acquire_lock(LOCK_KEY, 55 * 60):
        return 0

    today = datetime.now(timezone.utc).date()
    start, end = today - timedelta(days=DAYS_BEFORE), today + timedelta(days=DAYS_AFTER)
    try:
        if client is None:
            async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as own_client:
                events = await fetch_economic_calendar(own_client, settings.finnhub_api_key, start, end)
        else:
            events = await fetch_economic_calendar(client, settings.finnhub_api_key, start, end)
    except FinnhubNotAvailable as exc:
        logger.warning("Calendrier : %s", exc)
        sources.record_error(SOURCE_NAME, "Accès refusé par Finnhub : calendrier non inclus dans cette offre ou clé invalide")
        return 0
    except ProviderError as exc:
        logger.warning("Calendrier en échec : %s", exc)
        sources.record_error(SOURCE_NAME, "Source momentanément indisponible")
        cache.release_lock(LOCK_KEY)
        return 0

    sources.clear_error(SOURCE_NAME)
    count = await asyncio.to_thread(save_events, events)
    cache.delete_pattern("calendar:*")
    logger.info("Calendrier : %d événements enregistrés.", count)
    return count


if __name__ == "__main__":
    from app.core.logging import setup_logging

    setup_logging(get_settings().log_level)
    asyncio.run(run_fetch_calendar())
