"""Déduplication des news : hash SHA-256 du titre et de l'URL normalisés."""

import hashlib
import re
from collections.abc import Iterable
from typing import TypeVar
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.providers.base import RawNews

T = TypeVar("T", bound=RawNews)

_TRACKING_PREFIXES = ("utm_", "mc_", "fbclid", "gclid", "cmpid", "ncid")
_SPACE_RE = re.compile(r"\s+")


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(key, value) for key, value in parse_qsl(parts.query) if not key.lower().startswith(_TRACKING_PREFIXES)]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower() or "https", parts.netloc.lower(), path, urlencode(query), ""))


def normalize_title(title: str) -> str:
    return _SPACE_RE.sub(" ", title).strip().casefold()


def news_hash(title: str, url: str) -> str:
    key = f"{normalize_title(title)}|{normalize_url(url)}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def dedup(items: Iterable[T]) -> list[tuple[str, T]]:
    """Supprime les doublons d'un lot (on garde la première occurrence). Renvoie des couples (hash, news)."""
    seen: set[str] = set()
    unique: list[tuple[str, T]] = []
    for item in items:
        digest = news_hash(item.title, item.url)
        if digest not in seen:
            seen.add(digest)
            unique.append((digest, item))
    return unique
