"""Vérifie que chaque flux de app/data/rss_feeds.json répond et contient des news récentes.

Usage (depuis backend/) : python scripts/check_feeds.py
Code de sortie 1 si au moins un flux est en échec.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from app.providers.base import ProviderError  # noqa: E402
from app.providers.rss import rss_providers  # noqa: E402


async def main() -> int:
    failures = 0
    async with httpx.AsyncClient(timeout=20) as client:
        for provider in rss_providers():
            try:
                items = await provider.fetch(client)
            except ProviderError as exc:
                failures += 1
                print(f"ÉCHEC  {provider.feed.name:<40} {exc}")
                continue
            latest = max((item.published_at for item in items), default=None)
            status = "OK   " if items else "VIDE "
            print(f"{status}  {provider.feed.name:<40} {len(items):>3} news < 30 j, dernière : {latest or '—'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
