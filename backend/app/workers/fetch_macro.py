"""Tâche macro (1 fois par jour) : inflation et taux (FRED pour les États-Unis, Banque mondiale pour tous les pays).

Le scheduler la déclenche toutes les heures, mais chaque source n'est réellement appelée que si ses
données en base ont plus de 24 h : on obtient un appel par jour, avec un nouvel essai l'heure suivante
en cas d'échec (sans dépendre de Redis).
"""

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.logging import get_logger
from app.database import SessionLocal
from app.models import MacroIndicator
from app.providers.base import ProviderError
from app.providers.fred import FredProvider
from app.providers.worldbank import WorldBankProvider
from app.schemas.common import as_utc
from app.services import cache, pair_mapping, sources

logger = get_logger(__name__)
REFRESH_AFTER = timedelta(hours=24)
_warned_missing = False


def is_fresh(db: Session, source: str) -> bool:
    last = db.scalar(select(func.max(MacroIndicator.updated_at)).where(MacroIndicator.source == source))
    return last is not None and datetime.now(timezone.utc) - as_utc(last) < REFRESH_AFTER


def upsert_indicators(db: Session, rows: list[dict]) -> int:
    for row in rows:
        existing = db.scalar(
            select(MacroIndicator).where(
                MacroIndicator.country == row["country"],
                MacroIndicator.indicator == row["indicator"],
                MacroIndicator.source == row["source"],
            )
        )
        if existing is None:
            db.add(MacroIndicator(**row, updated_at=datetime.now(timezone.utc)))
        else:
            for key, value in row.items():
                setattr(existing, key, value)
            existing.updated_at = datetime.now(timezone.utc)
    db.commit()
    return len(rows)


def tracked_countries() -> list[str]:
    return sorted({info["country"] for info in pair_mapping.currencies().values() if info.get("country")})


async def run_fetch_macro(client: httpx.AsyncClient | None = None, force: bool = False) -> int:
    """Met à jour les indicateurs macro. Renvoie le nombre de lignes enregistrées."""
    global _warned_missing
    settings = get_settings()
    fred = FredProvider(settings.fred_api_key)
    worldbank = WorldBankProvider()

    with SessionLocal() as db:
        need_fred = fred.is_configured() and (force or not is_fresh(db, fred.name))
        need_worldbank = force or not is_fresh(db, worldbank.name)
    if not fred.is_configured() and not _warned_missing:
        logger.warning("FRED_API_KEY absente : inflation US mensuelle et taux Fed non disponibles (repli : Banque mondiale).")
        _warned_missing = True
    if not need_fred and not need_worldbank:
        return 0

    async def collect(http: httpx.AsyncClient) -> list[dict]:
        rows: list[dict] = []
        if need_fred:
            try:
                rows += await fred.fetch_us_indicators(http)
                sources.clear_error(fred.name)
            except ProviderError as exc:
                logger.warning("Macro FRED en échec : %s", exc)
                sources.record_error(fred.name, "Source momentanément indisponible")
        if need_worldbank:
            try:
                rows += await worldbank.fetch_inflation(http, tracked_countries())
                sources.clear_error(worldbank.name)
            except ProviderError as exc:
                logger.warning("Macro Banque mondiale en échec : %s", exc)
                sources.record_error(worldbank.name, "Source momentanément indisponible")
        return rows

    if client is None:
        async with httpx.AsyncClient(timeout=settings.http_timeout_seconds) as own_client:
            rows = await collect(own_client)
    else:
        rows = await collect(client)

    if not rows:
        return 0

    def save() -> int:
        with SessionLocal() as db:
            return upsert_indicators(db, rows)

    count = await asyncio.to_thread(save)
    cache.delete_pattern("macro:*")
    logger.info("Macro : %d indicateurs mis à jour.", count)
    return count


if __name__ == "__main__":
    from app.core.logging import setup_logging

    setup_logging(get_settings().log_level)
    asyncio.run(run_fetch_macro(force=True))
