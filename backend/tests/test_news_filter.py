import pytest

from app.services.news_filter import tag_news


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("ECB's Lagarde signals patience on rate cuts", {"EUR"}),
        ("Fed holds rates steady as Powell flags inflation risks", {"USD"}),
        ("EUR/USD climbs above 1.10 after US CPI miss", {"EUR", "USD"}),
        ("USDJPY slides as BoJ hints at hike", {"USD", "JPY"}),
        ("Gold hits record high on safe-haven demand", {"XAU"}),
        ("Bitcoin rallies past $100k", {"BTC", "CRYPTO"}),
        ("OPEC+ agrees to extend output cuts, crude jumps", {"OIL"}),
        ("Bank of England's Bailey: UK inflation still too high", {"GBP"}),
        ("Wall Street ends higher, Nasdaq leads", {"US_STOCKS"}),
        ("Bank Al-Maghrib keeps key rate unchanged", {"MAD"}),
    ],
)
def test_detects_tags_from_keywords(title, expected) -> None:
    assert set(tag_news(title)) == expected


def test_acronyms_are_case_sensitive() -> None:
    assert tag_news("Investors are fed up with volatility, says one of us") == []


def test_words_need_boundaries() -> None:
    assert tag_news("Goldman Sachs raises targets") == []


def test_default_tags_are_kept_and_summary_is_used() -> None:
    assert tag_news("Press release", "Monetary policy decision by the Swiss National Bank", ["CHF"]) == ["CHF"]
    assert tag_news("Daily wrap", "The yen weakened overnight") == ["JPY"]
