"""Correspondance paire -> devises / actifs -> pays, construite à partir de data/pairs_seed.json.

- news_tags   : étiquettes utilisées pour filtrer les news (devises + actifs : XAU, BTC, OIL...).
- macro_countries : pays dont on affiche l'inflation / les taux / le calendrier.
  * Forex : pays des deux devises.
  * Métaux et crypto : États-Unis (USD), plus le pays de la devise de cotation si différent.
  * Indices et matières premières : pays de la devise de cotation.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "pairs_seed.json"

# Actifs non monétaires : étiquettes de news associées.
ASSET_TAGS: dict[str, list[str]] = {
    "XAU": ["XAU"],
    "XAG": ["XAG"],
    "XPT": ["XPT"],
    "XPD": ["XPD"],
    "BTC": ["BTC", "CRYPTO"],
    "ETH": ["ETH", "CRYPTO"],
    "SOL": ["SOL", "CRYPTO"],
    "XRP": ["XRP", "CRYPTO"],
    "BNB": ["BNB", "CRYPTO"],
    "WTI": ["OIL"],
    "BRENT": ["OIL"],
    "NATGAS": ["NATGAS"],
    "DXY": [],
    "US30": ["US_STOCKS"],
    "SPX500": ["US_STOCKS"],
    "NAS100": ["US_STOCKS"],
    "GER40": ["DE_STOCKS"],
    "UK100": ["UK_STOCKS"],
    "FRA40": ["FR_STOCKS"],
    "JP225": ["JP_STOCKS"],
}

TAG_LABELS: dict[str, str] = {
    "XAU": "Or",
    "XAG": "Argent",
    "XPT": "Platine",
    "XPD": "Palladium",
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "XRP": "XRP",
    "BNB": "BNB",
    "CRYPTO": "Crypto",
    "OIL": "Pétrole",
    "NATGAS": "Gaz naturel",
    "US_STOCKS": "Actions US",
    "DE_STOCKS": "DAX",
    "UK_STOCKS": "FTSE",
    "FR_STOCKS": "CAC 40",
    "JP_STOCKS": "Nikkei",
}

# Codes pays alternatifs utilisés par certaines sources (Finnhub : "EU", "UK").
COUNTRY_ALIASES = {"EU": "EA", "UK": "GB", "EMU": "EA"}

USD_ANCHORED_CATEGORIES = {"metal", "crypto"}
QUOTE_ONLY_CATEGORIES = {"index", "commodity"}


@dataclass(frozen=True)
class Country:
    code: str
    name: str
    currency: str


@lru_cache
def load_seed() -> dict:
    with SEED_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def currencies() -> dict[str, dict]:
    return load_seed()["currencies"]


@lru_cache
def country_to_currency() -> dict[str, str]:
    mapping = {info["country"]: code for code, info in currencies().items() if info.get("country")}
    for alias, target in COUNTRY_ALIASES.items():
        if target in mapping:
            mapping[alias] = mapping[target]
    return mapping


def normalize_country(code: str) -> str:
    code = code.strip().upper()
    return COUNTRY_ALIASES.get(code, code)


def is_fiat(code: str) -> bool:
    info = currencies().get(code)
    return bool(info and info.get("country"))


def country_of(currency: str) -> str | None:
    info = currencies().get(currency)
    return info.get("country") if info else None


def country_info(code: str) -> Country | None:
    code = normalize_country(code)
    currency = country_to_currency().get(code)
    if not currency:
        return None
    return Country(code=code, name=currencies()[currency]["country_name"], currency=currency)


def news_tags(base: str, quote: str, category: str) -> list[str]:
    tags: list[str] = []
    for code in (base, quote):
        if is_fiat(code):
            tags.append(code)
        else:
            tags.extend(ASSET_TAGS.get(code, [code]))
    return list(dict.fromkeys(tags))


def macro_countries(base: str, quote: str, category: str) -> list[str]:
    if category in QUOTE_ONLY_CATEGORIES:
        codes = [quote]
    elif category in USD_ANCHORED_CATEGORIES:
        codes = ["USD", quote]
    else:
        codes = [base, quote]
    countries = [country_of(code) for code in codes if is_fiat(code)]
    result = [country for country in dict.fromkeys(countries) if country]
    return result or ["US"]


def macro_currencies(base: str, quote: str, category: str) -> list[str]:
    mapping = country_to_currency()
    return [mapping[country] for country in macro_countries(base, quote, category) if country in mapping]


def tag_label(tag: str) -> str:
    if tag in TAG_LABELS:
        return TAG_LABELS[tag]
    return tag
