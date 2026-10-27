from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.rate_limit import rate_limit
from app.database import get_db
from app.models import Pair
from app.schemas.pair import PairDetail, PairOut

router = APIRouter(prefix="/api/pairs", tags=["pairs"], dependencies=[Depends(rate_limit)])


def find_pair(db: Session, symbol: str) -> Pair | None:
    return db.scalar(select(Pair).where(func.upper(Pair.symbol) == symbol.strip().upper()))


def get_pair_or_404(db: Session, symbol: str) -> Pair:
    pair = find_pair(db, symbol)
    if pair is None:
        raise HTTPException(status_code=404, detail=f"Marché inconnu : {symbol}")
    return pair


@router.get("", response_model=list[PairOut])
def list_pairs(category: str | None = None, db: Session = Depends(get_db)) -> list[PairOut]:
    query = select(Pair).where(Pair.active.is_(True)).order_by(Pair.id)
    if category:
        query = query.where(Pair.category == category)
    return [PairOut.from_model(pair) for pair in db.scalars(query)]


@router.get("/{symbol}", response_model=PairDetail)
def get_pair(symbol: str, db: Session = Depends(get_db)) -> PairDetail:
    return PairDetail.from_model(get_pair_or_404(db, symbol))
