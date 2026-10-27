"""Initialisation de la base sans docker-entrypoint.sh (hébergement serverless type Vercel) :
migrations Alembic puis seed des paires, tous deux idempotents."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import get_settings
from app.database import SessionLocal
from app.seed import seed_pairs

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


def run_migrations() -> None:
    # Sans fichier .ini : alembic/env.py ne reconfigure pas les logs de l'application.
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))
    command.upgrade(config, "head")


def initialize_database() -> dict[str, int]:
    run_migrations()
    with SessionLocal() as db:
        created, updated = seed_pairs(db)
    return {"pairs_created": created, "pairs_updated": updated}
