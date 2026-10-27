"""Outils partagés par les tests : réponses HTTP simulées."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx

Handler = Callable[[httpx.Request], httpx.Response]


def mock_client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def rfc822(hours_ago: float) -> str:
    return format_datetime(datetime.now(timezone.utc) - timedelta(hours=hours_ago))


def rss_xml(items: list[dict]) -> str:
    body = "".join(
        f"""<item><title>{item['title']}</title><link>{item['link']}</link>
        <description>{item.get('description', '')}</description>
        {f"<pubDate>{item['pubDate']}</pubDate>" if item.get('pubDate') else ''}</item>"""
        for item in items
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title><link>https://example.com</link>{body}</channel></rss>"""
