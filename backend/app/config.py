"""Configuration de l'application, lue depuis les variables d'environnement / le fichier .env."""

import os
from functools import lru_cache
from typing import Annotated
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


DEFAULT_REDIS_URL = "redis://redis:6379/0"
# Hôtes de docker-compose / du poste local, injoignables depuis Vercel.
LOCAL_DB_HOSTS = {"db", "localhost", "127.0.0.1"}
# Base de secours sur Vercel tant qu'aucune vraie base (Neon...) n'est connectée : une par instance, effacée à l'arrêt.
VERCEL_FALLBACK_DATABASE_URL = "sqlite:////tmp/marketview.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://marketview:marketview_local@db:5432/marketview"
    # KV_URL : nom de la variable créée par l'intégration Upstash de Vercel. Vide = pas de Redis.
    redis_url: str = Field(default=DEFAULT_REDIS_URL, validation_alias=AliasChoices("REDIS_URL", "KV_URL"))
    # Liste séparée par des virgules (NoDecode : pas d'interprétation JSON de la variable).
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:5173"])

    finnhub_api_key: str = ""
    newsapi_key: str = ""
    marketaux_key: str = ""
    fred_api_key: str = ""
    tradingeconomics_key: str = ""
    twelvedata_key: str = ""
    jwt_secret: str = ""
    # Protège /api/cron/refresh (Vercel Cron envoie "Authorization: Bearer <CRON_SECRET>").
    cron_secret: str = ""

    log_level: str = "INFO"
    # Démarre APScheduler dans le processus de l'API (désactivé en production,
    # où un service "worker" dédié lance `python -m app.workers.scheduler`).
    run_scheduler: bool = True
    news_fetch_interval_seconds: int = 60
    rate_limit_per_minute: int = 120
    http_timeout_seconds: float = 15.0

    @property
    def on_vercel(self) -> bool:
        return bool(os.getenv("VERCEL"))

    @property
    def uses_fallback_database(self) -> bool:
        return self.database_url == VERCEL_FALLBACK_DATABASE_URL

    @field_validator("database_url", mode="after")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """Les hébergeurs (Neon, Vercel, Render...) fournissent postgres:// ; SQLAlchemy veut postgresql+psycopg://."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value

    @model_validator(mode="after")
    def serverless_defaults(self) -> "Settings":
        # Sur Vercel : pas de processus permanent (scheduler remplacé par /api/cron/refresh)
        # et pas de Redis "redis:6379" ni de PostgreSQL "db:5432" de docker-compose.
        if self.on_vercel:
            self.run_scheduler = False
            if self.redis_url == DEFAULT_REDIS_URL:
                self.redis_url = ""
            if not self.database_url or urlparse(self.database_url).hostname in LOCAL_DB_HOSTS:
                self.database_url = VERCEL_FALLBACK_DATABASE_URL
        return self

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator(
        "finnhub_api_key", "newsapi_key", "marketaux_key", "fred_api_key",
        "tradingeconomics_key", "twelvedata_key", "jwt_secret", "cron_secret", mode="before",
    )
    @classmethod
    def strip_keys(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
