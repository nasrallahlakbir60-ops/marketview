import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, ProgrammingError
from starlette.concurrency import run_in_threadpool

from app.api import auth, calendar, cron, macro, news, pairs, websocket
from app.config import get_settings
from app.core.logging import get_logger, request_id_var, setup_logging
from app.core.security import client_ip

settings = get_settings()
setup_logging(settings.log_level, json_format=settings.json_logs, log_file=settings.log_file)
logger = get_logger(__name__)
access_logger = get_logger("app.access")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    scheduler = None
    if settings.on_vercel:
        # Pas de docker-entrypoint.sh sur Vercel : migrations + seed (idempotents) au démarrage d'une instance.
        # En cas d'échec, les routes de données réessaient (dépendance ensure_database).
        from app.services.serverless import initialize_once

        try:
            await run_in_threadpool(initialize_once)
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


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Identifiant de requête (logs + en-tête X-Request-ID) et une ligne de log par requête API."""
    incoming = request.headers.get("x-request-id", "")
    request_id = incoming if REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        level = logging.WARNING if status_code >= 500 else logging.INFO
        access_logger.log(
            level,
            "%s %s %s %.1fms",
            request.method,
            request.url.path,
            status_code,
            duration_ms,
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": status_code,
                "duration_ms": duration_ms,
                "user_id": getattr(request.state, "user_id", None),
                "ip": client_ip(request),
            },
        )
        request_id_var.reset(token)


@app.exception_handler(OperationalError)
async def database_unavailable(_: Request, exc: OperationalError) -> JSONResponse:
    logger.error("Base de données indisponible : %s", exc.orig)
    return JSONResponse(status_code=503, content={"detail": "Service momentanément indisponible, réessayez dans un instant."})


@app.exception_handler(ProgrammingError)
async def database_not_initialized(_: Request, exc: ProgrammingError) -> JSONResponse:
    logger.error("Base de données non initialisée : %s", exc.orig)
    return JSONResponse(status_code=503, content={"detail": "Base de données en cours d'initialisation, réessayez dans un instant."})


app.include_router(auth.router)
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
