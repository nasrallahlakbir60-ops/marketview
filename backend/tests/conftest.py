"""Configuration commune des tests : SQLite en mémoire, fakeredis, aucune clé API, aucun appel réseau."""

import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["REDIS_URL"] = "redis://localhost:6399/0"
os.environ["RUN_SCHEDULER"] = "false"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
for key in ("FINNHUB_API_KEY", "FRED_API_KEY", "NEWSAPI_KEY", "MARKETAUX_KEY", "TRADINGECONOMICS_KEY", "TWELVEDATA_KEY"):
    os.environ[key] = ""

import fakeredis  # noqa: E402
import fakeredis.aioredis  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401
from app import redis_client  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.seed import seed_pairs  # noqa: E402


@pytest.fixture(autouse=True)
def fake_redis():
    server = fakeredis.FakeServer()
    sync_client = fakeredis.FakeRedis(server=server, decode_responses=True)
    async_client = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    redis_client.set_clients(sync_client, async_client)
    yield sync_client
    redis_client.set_clients(None, None)


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def seeded(db):
    seed_pairs(db)
    return db


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def settings():
    get_settings.cache_clear()
    current = get_settings()
    yield current
    get_settings.cache_clear()
