from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.pairs import get_pair_or_404
from app.config import get_settings
from app.core.rate_limit import rate_limit
from app.database import get_db
from app.models import MacroIndicator
from app.providers.fred import SOURCE as FRED
from app.providers.worldbank import SOURCE as WORLD_BANK
from app.schemas.macro import MacroCountryOut, MacroIndicatorOut, MacroResponse
from app.schemas.news import SourceStatus
from app.services import cache, pair_mapping, sources

router = APIRouter(prefix="/api/macro", tags=["macro"], dependencies=[Depends(rate_limit)])

# Pour un même indicateur, la donnée mensuelle de FRED est préférée à la donnée annuelle de la Banque mondiale.
SOURCE_PRIORITY = {FRED: 0, WORLD_BANK: 1}
INDICATOR_ORDER = ["CPI", "CORE_CPI", "INTEREST_RATE"]


def macro_sources() -> list[SourceStatus]:
    return [
        sources.status(FRED, bool(get_settings().fred_api_key), "FRED_API_KEY"),
        sources.status(WORLD_BANK, True),
    ]


def build_countries(db: Session, country_codes: list[str]) -> list[MacroCountryOut]:
    rows = db.scalars(select(MacroIndicator).where(MacroIndicator.country.in_(country_codes))).all()
    best: dict[tuple[str, str], MacroIndicator] = {}
    for row in rows:
        key = (row.country, row.indicator)
        current = best.get(key)
        if current is None or SOURCE_PRIORITY.get(row.source, 99) < SOURCE_PRIORITY.get(current.source, 99):
            best[key] = row

    countries = []
    for code in country_codes:
        info = pair_mapping.country_info(code)
        if info is None:
            continue
        indicators = sorted(
            (row for (country, _), row in best.items() if country == code),
            key=lambda row: INDICATOR_ORDER.index(row.indicator) if row.indicator in INDICATOR_ORDER else 99,
        )
        countries.append(
            MacroCountryOut(
                code=info.code,
                name=info.name,
                currency=info.currency,
                indicators=[MacroIndicatorOut.from_model(row) for row in indicators],
            )
        )
    return countries


@router.get("", response_model=MacroResponse)
def get_macro(pair: str = Query(..., description="Symbole de la paire, ex : EURUSD"), db: Session = Depends(get_db)) -> MacroResponse:
    """Inflation et taux des pays de la paire (lecture BDD + cache Redis 24 h, jamais d'appel externe ici)."""
    pair_row = get_pair_or_404(db, pair)
    key = f"macro:{pair_row.symbol}"
    cached = cache.get_json(key)
    if cached is not None:
        countries = [MacroCountryOut.model_validate(item) for item in cached]
    else:
        codes = pair_mapping.macro_countries(pair_row.base_currency, pair_row.quote_currency, pair_row.category)
        countries = build_countries(db, codes)
        # On ne met pas en cache une réponse vide (premier démarrage, données pas encore récupérées).
        if any(country.indicators for country in countries):
            cache.set_json(key, [country.model_dump(mode="json") for country in countries], cache.MACRO_TTL)
    return MacroResponse(pair=pair_row.symbol, countries=countries, sources=macro_sources())
