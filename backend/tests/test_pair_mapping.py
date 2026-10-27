import pytest

from app.services import pair_mapping


@pytest.mark.parametrize(
    ("base", "quote", "category", "tags", "countries"),
    [
        ("EUR", "USD", "forex_major", ["EUR", "USD"], ["EA", "US"]),
        ("USD", "JPY", "forex_major", ["USD", "JPY"], ["US", "JP"]),
        ("XAU", "USD", "metal", ["XAU", "USD"], ["US"]),
        ("XAU", "EUR", "metal", ["XAU", "EUR"], ["US", "EA"]),
        ("BTC", "USD", "crypto", ["BTC", "CRYPTO", "USD"], ["US"]),
        ("WTI", "USD", "commodity", ["OIL", "USD"], ["US"]),
        ("GER40", "EUR", "index", ["DE_STOCKS", "EUR"], ["EA"]),
        ("UK100", "GBP", "index", ["UK_STOCKS", "GBP"], ["GB"]),
        ("DXY", "USD", "index", ["USD"], ["US"]),
        ("USD", "MAD", "forex_exotic", ["USD", "MAD"], ["US", "MA"]),
    ],
)
def test_mapping(base, quote, category, tags, countries) -> None:
    assert pair_mapping.news_tags(base, quote, category) == tags
    assert pair_mapping.macro_countries(base, quote, category) == countries


def test_country_aliases() -> None:
    assert pair_mapping.country_to_currency()["EU"] == "EUR"
    assert pair_mapping.country_to_currency()["UK"] == "GBP"
    assert pair_mapping.country_info("eu").name == "Zone euro"
    assert pair_mapping.country_info("ZZ") is None


def test_macro_currencies() -> None:
    assert pair_mapping.macro_currencies("XAU", "USD", "metal") == ["USD"]
    assert pair_mapping.macro_currencies("EUR", "GBP", "forex_cross") == ["EUR", "GBP"]
