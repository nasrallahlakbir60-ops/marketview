from sqlalchemy import func, select

from app.models import Pair
from app.seed import seed_pairs
from app.services.pair_mapping import load_seed


def test_seed_is_idempotent(db) -> None:
    expected = len(load_seed()["pairs"])

    assert seed_pairs(db) == (expected, 0)
    assert seed_pairs(db) == (0, 0)
    assert db.scalar(select(func.count()).select_from(Pair)) == expected


def test_seed_updates_changed_rows(db) -> None:
    seed_pairs(db)
    pair = db.scalar(select(Pair).where(Pair.symbol == "EURUSD"))
    pair.name = "Ancien nom"
    db.commit()

    assert seed_pairs(db) == (0, 1)
    assert db.scalar(select(Pair.name).where(Pair.symbol == "EURUSD")) == "Euro / Dollar US"


def test_list_pairs(client, seeded) -> None:
    response = client.get("/api/pairs")

    assert response.status_code == 200
    pairs = response.json()
    assert len(pairs) == len(load_seed()["pairs"])
    assert pairs[0] == {
        "symbol": "EURUSD",
        "name": "Euro / Dollar US",
        "category": "forex_major",
        "base": "EUR",
        "quote": "USD",
        "tradingview_symbol": "OANDA:EURUSD",
        "active": True,
    }


def test_list_pairs_by_category(client, seeded) -> None:
    response = client.get("/api/pairs", params={"category": "crypto"})

    assert response.status_code == 200
    assert {pair["category"] for pair in response.json()} == {"crypto"}


def test_get_pair_detail_is_case_insensitive(client, seeded) -> None:
    response = client.get("/api/pairs/xauusd")

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "XAUUSD"
    assert [tag["code"] for tag in body["news_tags"]] == ["XAU", "USD"]
    assert body["news_tags"][0]["label"] == "Or"
    assert body["macro_countries"] == [{"code": "US", "name": "Etats-Unis", "currency": "USD"}]


def test_get_unknown_pair_returns_404(client, seeded) -> None:
    response = client.get("/api/pairs/NOPE")

    assert response.status_code == 404
    assert "NOPE" in response.json()["detail"]


def test_rate_limit_returns_429(client, seeded, monkeypatch) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "rate_limit_per_minute", 2)

    assert client.get("/api/pairs").status_code == 200
    assert client.get("/api/pairs").status_code == 200
    response = client.get("/api/pairs")
    assert response.status_code == 429
    assert "Retry-After" in response.headers
