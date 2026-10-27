from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.pairs import get_pair_or_404
from app.config import get_settings
from app.core.rate_limit import rate_limit
from app.database import get_db
from app.models import EconomicEvent
from app.schemas.macro import CalendarResponse, EconomicEventOut
from app.services import cache, pair_mapping, sources
from app.services.serverless import ensure_database, refresh_if_stale
from app.workers.fetch_calendar import SOURCE_NAME

router = APIRouter(prefix="/api/calendar", tags=["calendar"], dependencies=[Depends(rate_limit), Depends(ensure_database)])

RELATIVE_DAYS = {"yesterday": -1, "today": 0, "tomorrow": 1}


def parse_day(value: str) -> date:
    today = datetime.now(timezone.utc).date()
    if value in RELATIVE_DAYS:
        return today + timedelta(days=RELATIVE_DAYS[value])
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="day doit valoir today, tomorrow, yesterday ou AAAA-MM-JJ") from exc


@router.get("", response_model=CalendarResponse, dependencies=[Depends(refresh_if_stale("calendar"))])
def get_calendar(
    pair: str = Query(..., description="Symbole de la paire, ex : EURUSD"),
    day: str = Query("today", description="today, tomorrow, yesterday ou AAAA-MM-JJ (journée UTC)"),
    db: Session = Depends(get_db),
) -> CalendarResponse:
    """Événements économiques du jour (UTC) pour les devises de la paire (BDD + cache Redis 1 h)."""
    pair_row = get_pair_or_404(db, pair)
    target = parse_day(day)
    currencies = pair_mapping.macro_currencies(pair_row.base_currency, pair_row.quote_currency, pair_row.category)
    status = sources.status(SOURCE_NAME, bool(get_settings().finnhub_api_key), "FINNHUB_API_KEY")

    key = f"calendar:{pair_row.symbol}:{target.isoformat()}"
    cached = cache.get_json(key)
    if cached is not None:
        events = [EconomicEventOut.model_validate(item) for item in cached]
    else:
        start = datetime.combine(target, time.min, tzinfo=timezone.utc)
        rows = db.scalars(
            select(EconomicEvent)
            .where(
                EconomicEvent.currency.in_(currencies),
                EconomicEvent.event_time >= start,
                EconomicEvent.event_time < start + timedelta(days=1),
            )
            .order_by(EconomicEvent.event_time, EconomicEvent.id)
        )
        events = [EconomicEventOut.from_model(row) for row in rows]
        if events:
            cache.set_json(key, [event.model_dump(mode="json") for event in events], cache.CALENDAR_TTL)

    return CalendarResponse(pair=pair_row.symbol, day=target, currencies=currencies, events=events, source=status)
