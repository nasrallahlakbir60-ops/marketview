"""Planification des tâches (APScheduler).

- Dans l'API (dev) : démarré par main.py si RUN_SCHEDULER=true.
- En production : service dédié `python -m app.workers.scheduler` (l'API tourne avec RUN_SCHEDULER=false).
Les verrous Redis de chaque tâche empêchent les exécutions en double si plusieurs processus tournent.
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.database import SessionLocal
from app.services.auth import purge_expired
from app.workers.fetch_calendar import run_fetch_calendar
from app.workers.fetch_macro import run_fetch_macro
from app.workers.fetch_news import run_fetch_news

logger = get_logger(__name__)


def _safe(job: Callable[[], Awaitable[object]], name: str) -> Callable[[], Awaitable[None]]:
    async def runner() -> None:
        try:
            await job()
        except Exception:  # une tâche en échec ne doit jamais arrêter le scheduler
            logger.exception("Tâche %s en échec", name)

    runner.__name__ = name
    return runner


async def run_purge() -> dict[str, int]:
    """Sessions expirées et journal d'activité au-delà de AUDIT_RETENTION_DAYS."""

    def purge() -> dict[str, int]:
        with SessionLocal() as db:
            return purge_expired(db)

    return await asyncio.to_thread(purge)


def create_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    scheduler = AsyncIOScheduler(timezone="UTC")
    jobs: list[tuple[str, Callable[[], Awaitable[object]], dict, int]] = [
        ("fetch_news", run_fetch_news, {"seconds": settings.news_fetch_interval_seconds}, 3),
        # Vérifié toutes les heures, mais n'appelle les sources que si les données ont plus de 24 h.
        ("fetch_macro", run_fetch_macro, {"hours": 1}, 10),
        ("fetch_calendar", run_fetch_calendar, {"hours": 1}, 15),
        ("purge_expired", run_purge, {"hours": 6}, 60),
    ]
    for name, job, interval, delay in jobs:
        scheduler.add_job(
            _safe(job, name),
            "interval",
            id=name,
            next_run_time=now + timedelta(seconds=delay),
            max_instances=1,
            coalesce=True,
            misfire_grace_time=30,
            **interval,
        )
    return scheduler


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level, json_format=settings.json_logs, log_file=settings.log_file)
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler démarré : %s", ", ".join(job.id for job in scheduler.get_jobs()))
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    asyncio.run(main())
