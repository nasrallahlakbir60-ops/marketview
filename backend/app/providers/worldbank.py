"""API de la Banque mondiale : inflation annuelle (indice des prix à la consommation, % sur un an).

Gratuit, sans clé. Indicateur FP.CPI.TOTL.ZG. Données ANNUELLES, publiées avec plusieurs mois de retard :
l'année affichée est celle de la dernière valeur disponible.
Documentation : https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
"""

from datetime import date

import httpx

from app.providers.base import ProviderError

BASE_URL = "https://api.worldbank.org/v2"
INDICATOR = "FP.CPI.TOTL.ZG"
SOURCE = "Banque mondiale"
# Codes pays de l'application -> codes de la Banque mondiale (la zone euro est l'agrégat "EMU").
TO_WORLDBANK = {"EA": "EMU"}
TIMEOUT_SECONDS = 30.0
ATTEMPTS = 2


def source_url(country: str) -> str:
    location = "XC" if country == "EA" else country
    return f"https://data.worldbank.org/indicator/{INDICATOR}?locations={location}"


class WorldBankProvider:
    name = SOURCE

    def is_configured(self) -> bool:
        return True

    async def fetch_inflation(self, client: httpx.AsyncClient, countries: list[str]) -> list[dict]:
        codes = ";".join(TO_WORLDBANK.get(country, country) for country in countries)
        payload = None
        # L'API est parfois lente : délai plus long et un nouvel essai.
        for attempt in range(ATTEMPTS):
            try:
                response = await client.get(
                    f"{BASE_URL}/country/{codes}/indicator/{INDICATOR}",
                    params={"format": "json", "mrnev": 2, "per_page": 500},
                    timeout=TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                payload = response.json()
                break
            except (httpx.HTTPError, ValueError) as exc:
                if attempt == ATTEMPTS - 1:
                    raise ProviderError(f"Banque mondiale : {type(exc).__name__} {exc}".strip()) from exc

        if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
            raise ProviderError("Banque mondiale : format inattendu")
        try:
            release_date = date.fromisoformat(str(payload[0].get("lastupdated", ""))[:10])
        except ValueError:
            release_date = None

        by_country: dict[str, list[tuple[str, float]]] = {}
        for row in payload[1]:
            if row.get("value") is None:
                continue
            code = "EA" if row.get("countryiso3code") == "EMU" else str(row.get("country", {}).get("id", ""))
            if code in countries:
                by_country.setdefault(code, []).append((str(row["date"]), float(row["value"])))

        results = []
        for country, values in by_country.items():
            values.sort(reverse=True)
            (period, value), previous = values[0], values[1] if len(values) > 1 else (None, None)
            results.append(
                {
                    "country": country,
                    "indicator": "CPI",
                    "value": round(value, 2),
                    "previous": round(previous[1], 2) if previous[1] is not None else None,
                    "forecast": None,
                    "period": period,
                    "previous_period": previous[0],
                    "frequency": "annual",
                    "release_date": release_date,
                    "source": SOURCE,
                    "source_url": source_url(country),
                }
            )
        return results
