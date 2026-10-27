"""Charge data/pairs_seed.json dans la table pairs. Idempotent : `python -m app.seed` peut être relancé."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger, setup_logging
from app.database import SessionLocal
from app.models import Pair
from app.services.pair_mapping import load_seed

logger = get_logger(__name__)


def seed_pairs(db: Session) -> tuple[int, int]:
    """Insère les paires absentes et met à jour les existantes (clé : symbol). Renvoie (créées, mises à jour)."""
    existing = {pair.symbol: pair for pair in db.scalars(select(Pair))}
    created = updated = 0
    for item in load_seed()["pairs"]:
        values = {
            "name": item["name"],
            "category": item["category"],
            "base_currency": item["base"],
            "quote_currency": item["quote"],
            "tradingview_symbol": item["tradingview_symbol"],
            "active": bool(item.get("active", True)),
        }
        pair = existing.get(item["symbol"])
        if pair is None:
            db.add(Pair(symbol=item["symbol"], **values))
            created += 1
        elif any(getattr(pair, key) != value for key, value in values.items()):
            for key, value in values.items():
                setattr(pair, key, value)
            updated += 1
    db.commit()
    return created, updated


def main() -> None:
    setup_logging()
    with SessionLocal() as db:
        created, updated = seed_pairs(db)
    logger.info("Seed des paires terminé : %d créée(s), %d mise(s) à jour.", created, updated)


if __name__ == "__main__":
    main()
