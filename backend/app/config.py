"""Configuration de l'application, lue depuis les variables d'environnement / le fichier .env."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://marketview:marketview_local@db:5432/marketview"
    redis_url: str = "redis://redis:6379/0"
    # Liste séparée par des virgules (NoDecode : pas d'interprétation JSON de la variable).
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["http://localhost:5173"])

    finnhub_api_key: str = ""
    newsapi_key: str = ""
    marketaux_key: str = ""
    fred_api_key: str = ""
    tradingeconomics_key: str = ""
    twelvedata_key: str = ""
    jwt_secret: str = ""

    log_level: str = "INFO"
    # Démarre APScheduler dans le processus de l'API (désactivé en production,
    # où un service "worker" dédié lance `python -m app.workers.scheduler`).
    run_scheduler: bool = True
    news_fetch_interval_seconds: int = 60
    rate_limit_per_minute: int = 120
    http_timeout_seconds: float = 15.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator(
        "finnhub_api_key", "newsapi_key", "marketaux_key", "fred_api_key",
        "tradingeconomics_key", "twelvedata_key", "jwt_secret", mode="before",
    )
    @classmethod
    def strip_keys(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
