"""Flux RSS publics (sites d'actualité forex, banques centrales), lus avec feedparser."""

import calendar
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import httpx

from app.providers.base import USER_AGENT, NewsProvider, ProviderError, RawNews, clean_text, short_summary

FEEDS_PATH = Path(__file__).resolve().parent.parent / "data" / "rss_feeds.json"
# Les banques centrales publient peu : on garde 30 jours (le tri par date place le récent en haut).
MAX_AGE = timedelta(days=30)


@dataclass(frozen=True)
class FeedConfig:
    name: str
    url: str
    default_tags: list[str] = field(default_factory=list)


def load_feeds(path: Path = FEEDS_PATH) -> list[FeedConfig]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return [
        FeedConfig(name=item["name"], url=item["url"], default_tags=list(item.get("default_tags", [])))
        for item in data["feeds"]
        if item.get("enabled", True)
    ]


def _entry_datetime(entry: dict) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)


def _entry_image(entry: dict) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        for media in entry.get(key) or []:
            if media.get("url"):
                return media["url"]
    for link in entry.get("links") or []:
        if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image/") and link.get("href"):
            return link["href"]
    return None


class RssProvider(NewsProvider):
    def __init__(self, feed: FeedConfig) -> None:
        self.feed = feed
        self.name = f"RSS {feed.name}"

    async def fetch(self, client: httpx.AsyncClient) -> list[RawNews]:
        try:
            response = await client.get(self.feed.url, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"{self.name} : {exc}") from exc

        parsed = feedparser.parse(response.content)
        if parsed.bozo and not parsed.entries:
            raise ProviderError(f"{self.name} : flux illisible ({parsed.get('bozo_exception')})")

        oldest = datetime.now(timezone.utc) - MAX_AGE
        items: list[RawNews] = []
        for entry in parsed.entries:
            title = clean_text(entry.get("title"))
            url = entry.get("link")
            published_at = _entry_datetime(entry)
            # Sans date de publication fiable, on n'affiche pas la news (pas d'heure inventée).
            if not title or not url or published_at is None or published_at < oldest:
                continue
            items.append(
                RawNews(
                    title=title,
                    url=url,
                    source=self.feed.name,
                    published_at=min(published_at, datetime.now(timezone.utc)),
                    summary=short_summary(entry.get("summary") or entry.get("description")),
                    image_url=_entry_image(entry),
                    default_tags=self.feed.default_tags,
                )
            )
        return items


def rss_providers() -> list[RssProvider]:
    return [RssProvider(feed) for feed in load_feeds()]
