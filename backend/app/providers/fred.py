"""FRED (Federal Reserve Bank of St. Louis) : inflation US mensuelle et taux directeur de la Fed.

Documentation : https://fred.stlouisfed.org/docs/api/fred/
- CPI       : CPIAUCSL (indice des prix, mensuel) -> variation sur 12 mois en %.
- CORE_CPI  : CPILFESL (hors alimentation et énergie) -> variation sur 12 mois en %.
- INTEREST_RATE : DFEDTARU (borne haute de la cible des Fed funds, quotidien).
"""

from datetime import date

import httpx

from app.providers.base import ProviderError

BASE_URL = "https://api.stlouisfed.org/fred"
SOURCE = "FRED"


def series_url(series_id: str) -> str:
    return f"https://fred.stlouisfed.org/series/{series_id}"


class FredProvider:
    name = SOURCE

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get(self, client: httpx.AsyncClient, path: str, params: dict) -> dict:
        try:
            response = await client.get(
                f"{BASE_URL}{path}", params={**params, "api_key": self.api_key, "file_type": "json"}
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"FRED {path} : {exc}") from exc
        if response.status_code >= 400:
            # Le message d'erreur de FRED ne contient pas la clé ; l'URL, si (on ne la logue pas).
            raise ProviderError(f"FRED {path} : HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderError(f"FRED {path} : réponse non JSON") from exc

    async def observations(self, client: httpx.AsyncClient, series_id: str, limit: int) -> list[tuple[date, float]]:
        """Observations les plus récentes d'abord, sans les valeurs manquantes (".")."""
        data = await self._get(
            client, "/series/observations", {"series_id": series_id, "sort_order": "desc", "limit": limit}
        )
        result = []
        for item in data.get("observations", []):
            try:
                result.append((date.fromisoformat(item["date"]), float(item["value"])))
            except (KeyError, TypeError, ValueError):
                continue
        return result

    async def last_updated(self, client: httpx.AsyncClient, series_id: str) -> date | None:
        data = await self._get(client, "/series", {"series_id": series_id})
        try:
            return date.fromisoformat(data["seriess"][0]["last_updated"][:10])
        except (KeyError, IndexError, TypeError, ValueError):
            return None

    async def _yoy(self, client: httpx.AsyncClient, series_id: str, indicator: str) -> dict | None:
        obs = await self.observations(client, series_id, limit=14)
        if len(obs) < 13:
            return None
        current = round((obs[0][1] / obs[12][1] - 1) * 100, 2)
        previous = round((obs[1][1] / obs[13][1] - 1) * 100, 2) if len(obs) >= 14 else None
        return {
            "country": "US",
            "indicator": indicator,
            "value": current,
            "previous": previous,
            "forecast": None,
            "period": obs[0][0].strftime("%Y-%m"),
            "previous_period": obs[1][0].strftime("%Y-%m"),
            "frequency": "monthly",
            "release_date": await self.last_updated(client, series_id),
            "source": SOURCE,
            "source_url": series_url(series_id),
        }

    async def _policy_rate(self, client: httpx.AsyncClient) -> dict | None:
        obs = await self.observations(client, "DFEDTARU", limit=1500)
        if not obs:
            return None
        current = obs[0][1]
        effective_since = obs[0][0]
        previous = None
        for day, value in obs[1:]:
            if value != current:
                previous = value
                break
            effective_since = day
        return {
            "country": "US",
            "indicator": "INTEREST_RATE",
            "value": current,
            "previous": previous,
            "forecast": None,
            "period": effective_since.isoformat(),
            "previous_period": None,
            "frequency": "daily",
            "release_date": obs[0][0],
            "source": SOURCE,
            "source_url": series_url("DFEDTARU"),
        }

    async def fetch_us_indicators(self, client: httpx.AsyncClient) -> list[dict]:
        results = [
            await self._yoy(client, "CPIAUCSL", "CPI"),
            await self._yoy(client, "CPILFESL", "CORE_CPI"),
            await self._policy_rate(client),
        ]
        return [item for item in results if item]
