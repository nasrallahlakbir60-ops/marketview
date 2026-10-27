"""Finnhub : news de marché (forex, général, crypto) et calendrier économique.

Documentation : https://finnhub.io/docs/api. La clé est envoyée dans l'en-tête
X-Finnhub-Token (jamais dans l'URL, pour qu'elle n'apparaisse pas dans les logs).
"""

from datetime import date, datetime, timezone

import httpx

from app.providers.base import NewsProvider, ProviderError, RawNews, clean_text, short_summary

BASE_URL = "https://finnhub.io/api/v1"
NEWS_CATEGORIES = ("forex", "general", "crypto")
IMPACTS = {"low", "medium", "high"}


class FinnhubNotAvailable(ProviderError):
    """Clé refusée ou endpoint non inclus dans l'offre (401 / 403)."""


async def _get(client: httpx.AsyncClient, api_key: str, path: str, params: dict | None = None) -> object:
    try:
        response = await client.get(f"{BASE_URL}{path}", params=params, headers={"X-Finnhub-Token": api_key})
    except httpx.HTTPError as exc:
        raise ProviderError(f"Finnhub {path} : {exc}") from exc
    if response.status_code in (401, 403):
        raise FinnhubNotAvailable(f"Finnhub {path} : accès refusé ({response.status_code}), clé invalide ou offre insuffisante")
    if response.status_code == 429:
        raise ProviderError(f"Finnhub {path} : quota dépassé (429)")
    if response.status_code >= 400:
        raise ProviderError(f"Finnhub {path} : HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError(f"Finnhub {path} : réponse non JSON") from exc


class FinnhubNewsProvider(NewsProvider):
    name = "Finnhub"

    def __init__(self, api_key: str, categories: tuple[str, ...] = NEWS_CATEGORIES) -> None:
        self.api_key = api_key
        self.categories = categories

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def fetch(self, client: httpx.AsyncClient) -> list[RawNews]:
        items: list[RawNews] = []
        for category in self.categories:
            data = await _get(client, self.api_key, "/news", {"category": category})
            if not isinstance(data, list):
                raise ProviderError("Finnhub /news : format inattendu")
            for article in data:
                title = clean_text(article.get("headline"))
                url = article.get("url")
                timestamp = article.get("datetime")
                if not title or not url or not timestamp:
                    continue
                items.append(
                    RawNews(
                        title=title,
                        url=url,
                        source=clean_text(article.get("source")) or "Finnhub",
                        published_at=datetime.fromtimestamp(int(timestamp), tz=timezone.utc),
                        summary=short_summary(article.get("summary")),
                        image_url=article.get("image") or None,
                        default_tags=["CRYPTO"] if category == "crypto" else [],
                    )
                )
        return items


def _number(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _event_time(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    # Finnhub renvoie les heures du calendrier en UTC, sans fuseau explicite.
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


async def fetch_economic_calendar(client: httpx.AsyncClient, api_key: str, start: date, end: date) -> list[dict]:
    """Événements du calendrier économique entre deux dates (format normalisé)."""
    data = await _get(client, api_key, "/calendar/economic", {"from": start.isoformat(), "to": end.isoformat()})
    events = data.get("economicCalendar") if isinstance(data, dict) else None
    if not isinstance(events, list):
        raise ProviderError("Finnhub /calendar/economic : format inattendu")

    normalized = []
    for event in events:
        event_time = _event_time(event.get("time"))
        name = clean_text(event.get("event"))
        country = str(event.get("country") or "").strip().upper()
        if not event_time or not name or not country:
            continue
        impact = str(event.get("impact") or "").lower()
        normalized.append(
            {
                "country": country,
                "event_name": name[:200],
                "impact": impact if impact in IMPACTS else "low",
                "actual": _number(event.get("actual")),
                "forecast": _number(event.get("estimate")),
                "previous": _number(event.get("prev")),
                "unit": (str(event.get("unit")).strip() or None) if event.get("unit") else None,
                "event_time": event_time,
            }
        )
    return normalized
