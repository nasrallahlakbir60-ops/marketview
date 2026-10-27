from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, ProgrammingError
from starlette.concurrency import run_in_threadpool

from app.api import calendar, cron, macro, news, pairs, websocket
from app.config import get_settings
from app.core.logging import get_logger, setup_logging

settings = get_settings()
setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    scheduler = None
    if settings.on_vercel:
        # Pas de docker-entrypoint.sh sur Vercel : migrations + seed (idempotents) au démarrage d'une instance.
        from app.services.bootstrap import initialize_database

        try:
            await run_in_threadpool(initialize_database)
        except Exception:
            logger.exception("Initialisation de la base impossible (DATABASE_URL configurée ?)")
    if settings.run_scheduler:
        from app.workers.scheduler import create_scheduler

        scheduler = create_scheduler()
        scheduler.start()
        logger.info("Scheduler démarré dans le processus API.")
    yield
    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(title="MarketView API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(OperationalError)
async def database_unavailable(_: Request, exc: OperationalError) -> JSONResponse:
    logger.error("Base de données indisponible : %s", exc.orig)
    return JSONResponse(status_code=503, content={"detail": "Service momentanément indisponible, réessayez dans un instant."})


@app.exception_handler(ProgrammingError)
async def database_not_initialized(_: Request, exc: ProgrammingError) -> JSONResponse:
    logger.error("Base de données non initialisée : %s", exc.orig)
    return JSONResponse(status_code=503, content={"detail": "Base de données en cours d'initialisation, réessayez dans un instant."})


app.include_router(pairs.router)
app.include_router(news.router)
app.include_router(macro.router)
app.include_router(calendar.router)
app.include_router(websocket.router)
app.include_router(cron.router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Expose un statut minimal pour le contrôle de santé Docker."""
    return {"status": "ok"}
