"""ForexFactory (flux public faireconomy.media) : calendrier économique de la semaine, sans clé.

Le flux couvre la semaine en cours (dimanche -> samedi, heure de New York). Il fournit
l'impact, la prévision et la valeur précédente, mais pas la valeur réelle. Le site
limite les appels répétés : une requête par heure suffit largement.
"""

import re
from datetime import datetime, timezone

import httpx

from app.providers.base import ProviderError, clean_text

URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
IMPACTS = {"low": "low", "medium": "medium", "high": "high", "holiday": "low"}
# Codes devise du flux qui diffèrent de ceux des paires suivies.
CURRENCY_ALIASES = {"CNY": "CNH"}
# "3.7%", "-47", "18.5K", "<0.1%", "1.25M"...
VALUE_RE = re.compile(r"^[<>]?\s*(-?\d+(?:\.\d+)?)\s*([%KMBT]?)$", re.IGNORECASE)


def parse_value(raw: object) -> tuple[float | None, str | None]:
    """Valeur numérique et unité ("%", "K", "M", "B", "T") ; (None, None) si illisible."""
    match = VALUE_RE.match(str(raw or "").strip().replace(",", ""))
    if not match:
        return None, None
    return float(match.group(1)), match.group(2).upper() or None


async def fetch_week_calendar(client: httpx.AsyncClient) -> list[dict]:
    """Événements de la semaine, format normalisé (devise au lieu du pays)."""
    try:
        response = await client.get(URL, headers={"User-Agent": "MarketView/1.0"})
    except httpx.HTTPError as exc:
        raise ProviderError(f"ForexFactory : {exc}") from exc
    if response.status_code == 429:
        raise ProviderError("ForexFactory : trop de requêtes (429)")
    if response.status_code >= 400:
        raise ProviderError(f"ForexFactory : HTTP {response.status_code}")
    try:
        data = response.json()
    except ValueError as exc:
        raise ProviderError("ForexFactory : réponse non JSON") from exc
    if not isinstance(data, list):
        raise ProviderError("ForexFactory : format inattendu")

    normalized = []
    for event in data:
        name = clean_text(event.get("title"))
        currency = str(event.get("country") or "").strip().upper()
        try:
            event_time = datetime.fromisoformat(str(event.get("date"))).astimezone(timezone.utc)
        except ValueError:
            continue
        if not name or not currency:
            continue
        forecast, forecast_unit = parse_value(event.get("forecast"))
        previous, previous_unit = parse_value(event.get("previous"))
        normalized.append(
            {
                "currency": CURRENCY_ALIASES.get(currency, currency),
                "event_name": name[:200],
                "impact": IMPACTS.get(str(event.get("impact") or "").lower(), "low"),
                "actual": None,
                "forecast": forecast,
                "previous": previous,
                "unit": forecast_unit or previous_unit,
                "event_time": event_time,
            }
        )
    return normalized
