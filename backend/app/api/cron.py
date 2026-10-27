"""GET /api/cron/refresh : remplace le scheduler quand aucun processus permanent n'est possible (Vercel).

Appelé par Vercel Cron, GitHub Actions ou un service externe (cron-job.org) avec
l'en-tête "Authorization: Bearer <CRON_SECRET>". Initialise la base au besoin, puis
récupère news, macro (si données > 24 h) et calendrier (au plus 1 fois par heure).
"""

import secrets

from fastapi import APIRouter, Header, HTTPException
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.core.logging import get_logger
from app.services.bootstrap import initialize_database
from app.workers.fetch_calendar import run_fetch_calendar
from app.workers.fetch_macro import run_fetch_macro
from app.workers.fetch_news import run_fetch_news

router = APIRouter(prefix="/api/cron", tags=["cron"])
logger = get_logger(__name__)


def _check_secret(authorization: str | None) -> None:
    expected = get_settings().cron_secret
    if not expected:
        raise HTTPException(status_code=503, detail="CRON_SECRET non configuré sur le serveur.")
    if not authorization or not secrets.compare_digest(authorization, f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="Non autorisé.")


@router.get("/refresh")
async def refresh(authorization: str | None = Header(default=None)) -> dict:
    _check_secret(authorization)
    result: dict = await run_in_threadpool(initialize_database)
    for name, job in (("news", run_fetch_news), ("macro", run_fetch_macro), ("calendar", run_fetch_calendar)):
        try:
            result[name] = await job()
        except Exception:  # une source en échec ne doit pas bloquer les autres
            logger.exception("Cron : tâche %s en échec", name)
            result[name] = "erreur"
    logger.info("Cron refresh : %s", result)
    return result
