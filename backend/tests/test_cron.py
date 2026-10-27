from app.models import Pair


def test_cron_requires_configured_secret(client) -> None:
    assert client.get("/api/cron/refresh").status_code == 503


def test_cron_rejects_wrong_secret(client, settings, monkeypatch) -> None:
    monkeypatch.setattr(settings, "cron_secret", "s3cret")

    assert client.get("/api/cron/refresh").status_code == 401
    assert client.get("/api/cron/refresh", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_cron_initializes_and_runs_jobs(client, db, settings, monkeypatch) -> None:
    from app.api import cron

    monkeypatch.setattr(settings, "cron_secret", "s3cret")
    monkeypatch.setattr(cron, "initialize_database", lambda: {"pairs_created": 80, "pairs_updated": 0})

    async def fake_news():
        return 3

    async def failing_macro():
        raise RuntimeError("boom")

    async def fake_calendar():
        return 0

    monkeypatch.setattr(cron, "run_fetch_news", fake_news)
    monkeypatch.setattr(cron, "run_fetch_macro", failing_macro)
    monkeypatch.setattr(cron, "run_fetch_calendar", fake_calendar)

    response = client.get("/api/cron/refresh", headers={"Authorization": "Bearer s3cret"})

    assert response.status_code == 200
    assert response.json() == {"pairs_created": 80, "pairs_updated": 0, "news": 3, "macro": "erreur", "calendar": 0}


def test_initialize_database_runs_migrations_and_seed(tmp_path, monkeypatch) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.services import bootstrap

    url = f"sqlite:///{tmp_path / 'boot.db'}"
    monkeypatch.setattr(bootstrap.get_settings(), "database_url", url)
    engine = create_engine(url)
    monkeypatch.setattr(bootstrap, "SessionLocal", sessionmaker(bind=engine))

    assert bootstrap.initialize_database()["pairs_created"] == 80
    assert bootstrap.initialize_database()["pairs_created"] == 0
    with sessionmaker(bind=engine)() as session:
        assert session.query(Pair).count() == 80
    engine.dispose()
