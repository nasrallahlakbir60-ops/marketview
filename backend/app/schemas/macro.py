from datetime import date, datetime

from pydantic import BaseModel

from app.models import EconomicEvent, MacroIndicator
from app.schemas.common import as_utc
from app.schemas.news import SourceStatus

INDICATOR_LABELS = {
    ("CPI", "monthly"): "Inflation (IPC, sur 12 mois)",
    ("CPI", "annual"): "Inflation annuelle (IPC)",
    ("CORE_CPI", "monthly"): "Inflation sous-jacente (sur 12 mois)",
    ("INTEREST_RATE", "daily"): "Taux directeur Fed (borne haute)",
}


class MacroIndicatorOut(BaseModel):
    country: str
    indicator: str
    label: str
    value: float | None
    previous: float | None
    forecast: float | None
    period: str | None
    previous_period: str | None
    frequency: str | None
    release_date: date | None
    source: str
    source_url: str | None

    @classmethod
    def from_model(cls, row: MacroIndicator) -> "MacroIndicatorOut":
        return cls(
            country=row.country,
            indicator=row.indicator,
            label=INDICATOR_LABELS.get((row.indicator, row.frequency or ""), row.indicator),
            value=row.value,
            previous=row.previous,
            forecast=row.forecast,
            period=row.period,
            previous_period=row.previous_period,
            frequency=row.frequency,
            release_date=row.release_date,
            source=row.source,
            source_url=row.source_url,
        )


class MacroCountryOut(BaseModel):
    code: str
    name: str
    currency: str
    indicators: list[MacroIndicatorOut]


class MacroResponse(BaseModel):
    pair: str
    countries: list[MacroCountryOut]
    sources: list[SourceStatus]


class EconomicEventOut(BaseModel):
    country: str
    currency: str | None
    event_name: str
    impact: str
    actual: float | None
    forecast: float | None
    previous: float | None
    unit: str | None
    event_time: datetime

    @classmethod
    def from_model(cls, row: EconomicEvent) -> "EconomicEventOut":
        return cls(
            country=row.country,
            currency=row.currency,
            event_name=row.event_name,
            impact=row.impact,
            actual=row.actual,
            forecast=row.forecast,
            previous=row.previous,
            unit=row.unit,
            event_time=as_utc(row.event_time),
        )


class CalendarResponse(BaseModel):
    pair: str
    day: date
    currencies: list[str]
    events: list[EconomicEventOut]
    source: SourceStatus
