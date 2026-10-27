from datetime import datetime, timezone

from app.providers.base import RawNews
from app.services.dedup import dedup, news_hash, normalize_url


def _news(title: str, url: str) -> RawNews:
    return RawNews(title=title, url=url, source="Test", published_at=datetime.now(timezone.utc))


def test_normalize_url_removes_tracking_and_fragment() -> None:
    assert normalize_url("HTTPS://Example.com/a/b/?utm_source=x&id=3#top") == "https://example.com/a/b?id=3"


def test_hash_ignores_case_spaces_and_tracking() -> None:
    assert news_hash("Fed  holds rates", "https://x.com/n?utm_medium=rss") == news_hash("fed holds rates", "https://x.com/n")
    assert news_hash("Fed holds rates", "https://x.com/a") != news_hash("Fed holds rates", "https://x.com/b")


def test_dedup_keeps_first_occurrence() -> None:
    first = _news("Gold rises", "https://a.com/1")
    items = [first, _news("GOLD RISES", "https://a.com/1/"), _news("Silver rises", "https://a.com/2")]

    result = dedup(items)

    assert [item for _, item in result] == [first, items[2]]
