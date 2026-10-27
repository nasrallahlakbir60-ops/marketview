"""Hébergement serverless (Vercel) : pas de docker-entrypoint.sh ni de scheduler permanent.

Dépendances FastAPI qui, sur Vercel uniquement, initialisent la base une fois par instance
puis rafraîchissent news / macro / calendrier à la demande quand les données sont trop
anciennes. /api/cron/refresh reste utile pour garder les données à jour sans visite.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable

from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.core.logging import get_logger
from app.services.bootstrap import initialize_database
from app.workers.fetch_calendar import run_fetch_calendar
from app.workers.fetch_macro import run_fetch_macro
from app.workers.fetch_news import run_fetch_news

logger = get_logger(__name__)

# Délai minimal entre deux rafraîchissements d'une même instance, en secondes.
REFRESH_INTERVALS = {"news": 300, "macro": 3600, "calendar": 3600}
JOBS: dict[str, Callable[[], Awaitable[object]]] = {
    "news": run_fetch_news,
    "macro": run_fetch_macro,
    "calendar": run_fetch_calendar,
}
# Laisse le temps de répondre avant la limite de 60 s de la fonction Vercel.
JOB_TIMEOUT_SECONDS = 40

_database_ready = False
_last_refresh: dict[str, float] = {}
_running: set[str] = set()


def initialize_once() -> None:
    global _database_ready
    if _database_ready:
        return
    settings = get_settings()
    if settings.uses_fallback_database:
        logger.warning(
            "DATABASE_URL absente ou locale (docker) : base SQLite temporaire %s. "
            "Connectez Neon au projet Vercel pour conserver les données.",
            settings.database_url,
        )
    initialize_database()
    _database_ready = True


async def ensure_database() -> None:
    if get_settings().on_vercel and not _database_ready:
        await run_in_threadpool(initialize_once)


def refresh_if_stale(kind: str) -> Callable[[], Awaitable[None]]:
    async def dependency() -> None:
        if not get_settings().on_vercel or kind in _running:
            return
        now = time.monotonic()
        last = _last_refresh.get(kind)
        if last is not None and now - last < REFRESH_INTERVALS[kind]:
            return
        _running.add(kind)
        _last_refresh[kind] = now  # même en cas d'échec : pas de nouvel essai à chaque requête
        try:
            await asyncio.wait_for(JOBS[kind](), timeout=JOB_TIMEOUT_SECONDS)
        except Exception:  # la route sert alors les données déjà en base
            logger.exception("Rafraîchissement %s à la demande en échec", kind)
        finally:
            _running.discard(kind)

    return dependency
