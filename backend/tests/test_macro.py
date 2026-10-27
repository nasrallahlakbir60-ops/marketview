import asyncio
from datetime import date, datetime, timedelta, timezone

import httpx
import pytest

from app.models import EconomicEvent, MacroIndicator
from app.providers.base import ProviderError
from app.providers.fred import FredProvider
from app.providers.worldbank import WorldBankProvider
from app.workers import fetch_calendar, fetch_macro
from tests.helpers import mock_client


def run(coro):
    return asyncio.run(coro)


# --- Réponses simulées ------------------------------------------------------------------

def _monthly(values: list[float], start: date = date(2026, 9, 1)) -> list[dict]:
    """Observations FRED, la plus récente d'abord."""
    result, year, month = [], start.year, start.month
    for value in values:
        result.append({"date": f"{year:04d}-{month:02d}-01", "value": str(value)})
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return result


CPI = _monthly([103.0, 102.5] + [101.0] * 10 + [100.0, 100.0])
RATE = [{"date": "2026-10-26", "value": "4.00"}, {"date": "2026-10-25", "value": "4.00"},
        {"date": "2026-09-17", "value": "4.00"}, {"date": "2026-09-16", "value": "4.25"}, {"date": "2026-09-15", "value": "."}]


def fred_handler(request: httpx.Request) -> httpx.Response:
    series = request.url.params["series_id"]
    if request.url.path.endswith("/series"):
        return httpx.Response(200, json={"seriess": [{"id": series, "last_updated": "2026-10-15 07:43:02-05"}]})
    observations = RATE if series == "DFEDTARU" else CPI
    return httpx.Response(200, json={"observations": observations})


WORLDBANK_PAYLOAD = [
    {"page": 1, "lastupdated": "2026-10-08"},
    [
        {"country": {"id": "XC", "value": "Euro area"}, "countryiso3code": "EMU", "date": "2025", "value": 2.466},
        {"country": {"id": "XC", "value": "Euro area"}, "countryiso3code": "EMU", "date": "2024", "value": 2.256},
        {"country": {"id": "US", "value": "United States"}, "countryiso3code": "USA", "date": "2024", "value": 2.95},
        {"country": {"id": "US", "value": "United States"}, "countryiso3code": "USA", "date": "2023", "value": 4.12},
        {"country": {"id": "MA", "value": "Morocco"}, "countryiso3code": "MAR", "date": "2025", "value": None},
    ],
]


def macro_handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "api.worldbank.org":
        return httpx.Response(200, json=WORLDBANK_PAYLOAD)
    return fred_handler(request)


async def _with_client(handler, func):
    async with mock_client(handler) as client:
        return await func(client)


# --- Providers --------------------------------------------------------------------------

def test_fred_computes_year_over_year_and_policy_rate() -> None:
    rows = run(_with_client(fred_handler, FredProvider("k" * 32).fetch_us_indicators))
    by_indicator = {row["indicator"]: row for row in rows}

    cpi = by_indicator["CPI"]
    assert cpi["value"] == 3.0  # 103 / 100
    assert cpi["previous"] == 2.5  # 102.5 / 100
    assert cpi["period"] == "2026-09"
    assert cpi["release_date"] == date(2026, 10, 15)
    assert cpi["forecast"] is None

    rate = by_indicator["INTEREST_RATE"]
    assert rate["value"] == 4.0
    assert rate["previous"] == 4.25
    assert rate["period"] == "2026-09-17"


def test_fred_http_error_raises() -> None:
    with pytest.raises(ProviderError):
        run(_with_client(lambda request: httpx.Response(400, json={}), FredProvider("bad").fetch_us_indicators))


def test_fred_not_configured_without_key() -> None:
    assert FredProvider("").is_configured() is False


def test_worldbank_parses_latest_two_values_per_country() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "EMU" in request.url.path  # la zone euro est demandée avec le code EMU
        return httpx.Response(200, json=WORLDBANK_PAYLOAD)

    rows = run(_with_client(handler, lambda client: WorldBankProvider().fetch_inflation(client, ["EA", "US", "MA"])))
    by_country = {row["country"]: row for row in rows}

    assert set(by_country) == {"EA", "US"}  # pas de valeur inventée pour le Maroc
    assert by_country["EA"]["value"] == 2.47
    assert by_country["EA"]["previous"] == 2.26
    assert by_country["EA"]["period"] == "2025"
    assert by_country["US"]["frequency"] == "annual"
    assert by_country["US"]["release_date"] == date(2026, 10, 8)


def test_worldbank_bad_payload_raises() -> None:
    with pytest.raises(ProviderError):
        run(_with_client(lambda request: httpx.Response(200, json={"message": "x"}),
                         lambda client: WorldBankProvider().fetch_inflation(client, ["US"])))


# --- Worker + route macro ---------------------------------------------------------------

def test_fetch_macro_without_fred_key_uses_worldbank_only(seeded) -> None:
    count = run(_with_client(macro_handler, fetch_macro.run_fetch_macro))

    assert count == 2
    assert {row.source for row in seeded.query(MacroIndicator)} == {"Banque mondiale"}
    # Données fraîches : pas de nouvel appel avant 24 h.
    assert run(_with_client(macro_handler, fetch_macro.run_fetch_macro)) == 0


def test_macro_route_prefers_fred_and_reports_sources(client, seeded, settings, monkeypatch) -> None:
    monkeypatch.setattr(settings, "fred_api_key", "k" * 32)
    run(_with_client(macro_handler, fetch_macro.run_fetch_macro))

    body = client.get("/api/macro", params={"pair": "EURUSD"}).json()

    assert body["pair"] == "EURUSD"
    assert [country["code"] for country in body["countries"]] == ["EA", "US"]
    us = body["countries"][1]["indicators"]
    assert [item["indicator"] for item in us] == ["CPI", "CORE_CPI", "INTEREST_RATE"]
    assert us[0]["source"] == "FRED"
    assert us[0]["label"] == "Inflation (IPC, sur 12 mois)"
    assert body["countries"][0]["indicators"][0]["source"] == "Banque mondiale"
    assert all(source["configured"] for source in body["sources"])


def test_macro_route_without_data_and_without_key(client, seeded) -> None:
    body = client.get("/api/macro", params={"pair": "XAUUSD"}).json()

    assert body["countries"] == [{"code": "US", "name": "Etats-Unis", "currency": "USD", "indicators": []}]
    fred = next(source for source in body["sources"] if source["name"] == "FRED")
    assert fred == {"name": "FRED", "configured": False, "message": "Source non configurée (FRED_API_KEY absente du .env)"}


def test_macro_route_caches_non_empty_response(client, seeded, fake_redis) -> None:
    client.get("/api/macro", params={"pair": "EURUSD"})
    assert fake_redis.get("macro:EURUSD") is None  # réponse vide non mise en cache

    run(_with_client(macro_handler, fetch_macro.run_fetch_macro))
    client.get("/api/macro", params={"pair": "EURUSD"})
    assert 0 < fake_redis.ttl("macro:EURUSD") <= 24 * 3600


def test_macro_route_unknown_pair(client, seeded) -> None:
    assert client.get("/api/macro", params={"pair": "NOPE"}).status_code == 404


# --- Calendrier -------------------------------------------------------------------------

def _calendar_handler(request: httpx.Request) -> httpx.Response:
    today = datetime.now(timezone.utc).date().isoformat()
    return httpx.Response(200, json={"economicCalendar": [
        {"country": "US", "event": "CPI YoY", "impact": "high", "estimate": 2.9, "prev": 3.0, "time": f"{today} 12:30:00", "unit": "%"},
        {"country": "EU", "event": "ECB President Speech", "impact": "medium", "time": f"{today} 08:00:00"},
        {"country": "JP", "event": "Tankan", "impact": "high", "time": f"{today} 23:50:00"},
        {"country": "XX", "event": "Unknown country", "impact": "low", "time": f"{today} 10:00:00"},
    ]})


def test_fetch_calendar_skipped_without_key(seeded) -> None:
    assert run(_with_client(_calendar_handler, fetch_calendar.run_fetch_calendar)) == 0


def test_fetch_calendar_and_route(client, seeded, settings, monkeypatch) -> None:
    monkeypatch.setattr(settings, "finnhub_api_key", "key")

    assert run(_with_client(_calendar_handler, fetch_calendar.run_fetch_calendar)) == 3
    assert seeded.query(EconomicEvent).filter_by(country="EA").one().currency == "EUR"

    body = client.get("/api/calendar", params={"pair": "EURUSD", "day": "today"}).json()

    assert body["currencies"] == ["EUR", "USD"]
    assert [event["event_name"] for event in body["events"]] == ["ECB President Speech", "CPI YoY"]
    assert body["events"][1]["impact"] == "high"
    assert body["events"][1]["forecast"] == 2.9
    assert body["events"][1]["actual"] is None
    assert body["source"]["configured"] is True

    tomorrow = client.get("/api/calendar", params={"pair": "EURUSD", "day": "tomorrow"}).json()
    assert tomorrow["events"] == []


def test_fetch_calendar_forbidden_is_reported(client, seeded, settings, monkeypatch) -> None:
    monkeypatch.setattr(settings, "finnhub_api_key", "free-key")

    assert run(_with_client(lambda request: httpx.Response(403, json={}), fetch_calendar.run_fetch_calendar)) == 0

    source = client.get("/api/calendar", params={"pair": "EURUSD"}).json()["source"]
    assert source["configured"] is True
    assert "Accès refusé" in source["message"]


def test_calendar_route_without_key_and_bad_day(client, seeded) -> None:
    body = client.get("/api/calendar", params={"pair": "XAUUSD"}).json()
    assert body["currencies"] == ["USD"]
    assert body["events"] == []
    assert body["source"]["message"].startswith("Source non configurée")

    assert client.get("/api/calendar", params={"pair": "EURUSD", "day": "hier"}).status_code == 422
    assert client.get("/api/calendar", params={"pair": "EURUSD", "day": "2026-10-27"}).status_code == 200


def test_old_events_are_purged(seeded, settings, monkeypatch) -> None:
    seeded.add(EconomicEvent(country="US", currency="USD", event_name="Old", impact="low",
                             event_time=datetime.now(timezone.utc) - timedelta(days=30), source="Finnhub"))
    seeded.commit()
    monkeypatch.setattr(settings, "finnhub_api_key", "key")

    run(_with_client(_calendar_handler, fetch_calendar.run_fetch_calendar))

    assert seeded.query(EconomicEvent).filter_by(event_name="Old").count() == 0
