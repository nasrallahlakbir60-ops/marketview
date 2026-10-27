from app.config import Settings


def test_cors_origins_accepts_comma_separated_env(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173, https://marketview.example")

    assert Settings().cors_origins == ["http://localhost:5173", "https://marketview.example"]


def test_api_keys_are_stripped(monkeypatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", "  abc  ")

    assert Settings().fred_api_key == "abc"


def test_postgres_urls_use_psycopg_driver(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@ep-x.neon.tech/db?sslmode=require")

    assert Settings().database_url == "postgresql+psycopg://u:p@ep-x.neon.tech/db?sslmode=require"


def test_vercel_defaults(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("RUN_SCHEDULER", "true")

    settings = Settings()

    assert settings.run_scheduler is False
    assert settings.redis_url == ""


def test_upstash_kv_url_is_accepted(monkeypatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("KV_URL", "rediss://default:x@eu1.upstash.io:6379")

    assert Settings().redis_url == "rediss://default:x@eu1.upstash.io:6379"
