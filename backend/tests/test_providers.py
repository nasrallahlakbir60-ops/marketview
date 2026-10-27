import asyncio
from datetime import date

import httpx
import pytest

from app.providers.base import ProviderError, short_summary
from app.providers.finnhub import FinnhubNewsProvider, FinnhubNotAvailable, fetch_economic_calendar
from app.providers.rss import FeedConfig, RssProvider, load_feeds
from tests.helpers import mock_client, rfc822, rss_xml


def run(coro):
    return asyncio.run(coro)


async def _fetch(provider, handler):
    async with mock_client(handler) as client:
        return await provider.fetch(client)


# --- RSS ---------------------------------------------------------------------------------

def test_rss_provider_parses_recent_entries() -> None:
    xml = rss_xml([
        {"title": "ECB holds rates", "link": "https://ecb.example/1", "description": "<p>The <b>ECB</b> kept rates.</p>", "pubDate": rfc822(1)},
        {"title": "Old news", "link": "https://ecb.example/2", "pubDate": rfc822(24 * 60)},
        {"title": "No date", "link": "https://ecb.example/3"},
    ])
    provider = RssProvider(FeedConfig(name="BCE", url="https://ecb.example/rss", default_tags=["EUR"]))

    items = run(_fetch(provider, lambda request: httpx.Response(200, text=xml)))

    assert len(items) == 1
    assert items[0].title == "ECB holds rates"
    assert items[0].summary == "The ECB kept rates."
    assert items[0].source == "BCE"
    assert items[0].default_tags == ["EUR"]
    assert items[0].published_at.tzinfo is not None


def test_rss_provider_raises_on_http_error() -> None:
    provider = RssProvider(FeedConfig(name="Down", url="https://down.example/rss"))

    with pytest.raises(ProviderError):
        run(_fetch(provider, lambda request: httpx.Response(503)))


def test_feeds_file_is_valid() -> None:
    feeds = load_feeds()
    assert len(feeds) >= 5
    assert all(feed.url.startswith("https://") for feed in feeds)
    assert len({feed.url for feed in feeds}) == len(feeds)


def test_short_summary_never_copies_full_article() -> None:
    summary = short_summary("mot " * 500)
    assert len(summary) <= 280
    assert summary.endswith("…")


# --- Finnhub -----------------------------------------------------------------------------

def test_finnhub_not_configured_without_key() -> None:
    assert FinnhubNewsProvider("").is_configured() is False
    assert FinnhubNewsProvider("abc").is_configured() is True


def test_finnhub_news_uses_header_token_and_parses() -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[
            {"headline": "Dollar firms", "url": "https://n.example/1", "source": "Reuters", "summary": "USD up",
             "datetime": 1_790_000_000, "image": ""},
            {"headline": "", "url": "https://n.example/2", "datetime": 1_790_000_000},
        ])

    items = run(_fetch(FinnhubNewsProvider("secret", categories=("forex",)), handler))

    assert len(items) == 1
    assert items[0].source == "Reuters"
    assert items[0].image_url is None
    assert seen[0].headers["X-Finnhub-Token"] == "secret"
    assert "secret" not in str(seen[0].url)


def test_finnhub_forbidden_raises_specific_error() -> None:
    with pytest.raises(FinnhubNotAvailable):
        run(_fetch(FinnhubNewsProvider("bad", categories=("forex",)), lambda request: httpx.Response(403, json={})))


def test_finnhub_calendar_normalizes_events() -> None:
    payload = {"economicCalendar": [
        {"country": "US", "event": "CPI YoY", "impact": "high", "actual": None, "estimate": 2.9, "prev": "3.0",
         "time": "2026-10-27 12:30:00", "unit": "%"},
        {"country": "EU", "event": "ECB speech", "impact": "", "time": "2026-10-27 08:00:00"},
        {"country": "", "event": "Ignored", "time": "2026-10-27 08:00:00"},
    ]}

    async def go():
        async with mock_client(lambda request: httpx.Response(200, json=payload)) as client:
            return await fetch_economic_calendar(client, "key", date(2026, 10, 27), date(2026, 10, 28))

    events = run(go())

    assert len(events) == 2
    assert events[0]["forecast"] == 2.9
    assert events[0]["previous"] == 3.0
    assert events[0]["actual"] is None
    assert events[0]["event_time"].isoformat() == "2026-10-27T12:30:00+00:00"
    assert events[1]["impact"] == "low"
