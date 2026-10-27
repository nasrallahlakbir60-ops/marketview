import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx

from app.models import News
from app.providers.base import RawNews
from app.providers.rss import FeedConfig, RssProvider
from app.redis_client import NEWS_CHANNEL
from app.services.news_store import save_news
from app.workers import fetch_news
from tests.helpers import mock_client, rfc822, rss_xml


def _raw(title: str, minutes_ago: int, url: str | None = None, tags: list[str] | None = None) -> RawNews:
    return RawNews(
        title=title,
        url=url or f"https://n.example/{abs(hash(title))}",
        source="Test",
        published_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        default_tags=tags or [],
    )


def test_save_news_tags_dedups_and_skips_untagged(db) -> None:
    items = [_raw("ECB keeps rates", 5), _raw("ECB keeps rates", 5), _raw("Local weather update", 1)]

    created = save_news(db, items)

    assert [news.title for news in created] == ["ECB keeps rates"]
    assert created[0].currencies == ["EUR"]
    assert save_news(db, items) == []


def test_news_route_filters_by_pair_and_sorts(client, seeded, db) -> None:
    save_news(db, [
        _raw("ECB keeps rates", 30),
        _raw("Fed signals cut", 5),
        _raw("BoJ hike ahead", 1),
        _raw("Gold rallies", 2),
    ])

    response = client.get("/api/news", params={"pair": "EURUSD"})

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Fed signals cut", "ECB keeps rates"]
    first = response.json()[0]
    assert set(first) == {"id", "title", "summary", "url", "source", "image_url", "published_at", "currencies"}
    assert first["currencies"] == ["USD"]


def test_news_route_limit_and_validation(client, seeded, db) -> None:
    save_news(db, [_raw(f"Fed headline {index}", index) for index in range(5)])

    assert len(client.get("/api/news", params={"pair": "EURUSD", "limit": 2}).json()) == 2
    assert client.get("/api/news", params={"pair": "EURUSD", "limit": 500}).status_code == 422
    assert client.get("/api/news").status_code == 422
    assert client.get("/api/news", params={"pair": "NOPE"}).status_code == 404


def test_news_route_uses_cache(client, seeded, db, fake_redis) -> None:
    save_news(db, [_raw("Fed signals cut", 5)])
    assert len(client.get("/api/news", params={"pair": "EURUSD"}).json()) == 1
    assert fake_redis.ttl("news:EURUSD:50") <= 60

    save_news(db, [_raw("Fed second headline", 1)])
    assert len(client.get("/api/news", params={"pair": "EURUSD"}).json()) == 1  # servi depuis le cache


def test_news_sources_reports_missing_key(client) -> None:
    body = client.get("/api/news/sources").json()

    finnhub = next(item for item in body if item["name"] == "Finnhub")
    assert finnhub["configured"] is False
    assert finnhub["message"].startswith("Source non configurée")


def test_fetch_news_pipeline_stores_and_publishes(seeded, fake_redis, monkeypatch) -> None:
    xml = rss_xml([
        {"title": "Fed holds rates steady", "link": "https://fed.example/1", "pubDate": rfc822(0.5)},
        {"title": "Weather report", "link": "https://fed.example/2", "pubDate": rfc822(0.5)},
    ])
    monkeypatch.setattr(fetch_news, "rss_providers", lambda: [RssProvider(FeedConfig(name="Fed", url="https://fed.example/rss"))])
    pubsub = fake_redis.pubsub()
    pubsub.subscribe(NEWS_CHANNEL)
    pubsub.get_message(timeout=1)
    fake_redis.set("news:EURUSD:50", "[]")

    async def go():
        async with mock_client(lambda request: httpx.Response(200, text=xml)) as client:
            return await fetch_news.run_fetch_news(client)

    assert asyncio.run(go()) == 1
    assert seeded.query(News).count() == 1
    assert fake_redis.get("news:EURUSD:50") is None  # cache invalidé
    message = pubsub.get_message(timeout=1)
    assert json.loads(message["data"])["title"] == "Fed holds rates steady"
    # Le verrou empêche une deuxième exécution immédiate (quota des API).
    assert asyncio.run(go()) == 0


def test_fetch_news_survives_failing_source(seeded, monkeypatch) -> None:
    class Broken(fetch_news.NewsProvider):
        name = "Broken"

        async def fetch(self, client):
            raise fetch_news.ProviderError("boom")

    monkeypatch.setattr(fetch_news, "build_providers", lambda: [Broken()])

    async def go():
        async with mock_client(lambda request: httpx.Response(500)) as client:
            return await fetch_news.run_fetch_news(client)

    assert asyncio.run(go()) == 0
