"""Format commun des news et classe abstraite des fournisseurs (1 fichier = 1 source externe)."""

import html
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

import httpx

SUMMARY_MAX_LENGTH = 280
USER_AGENT = "MarketView/1.0 (+https://github.com/; lecteur de titres financiers)"

_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


@dataclass
class RawNews:
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str | None = None
    image_url: str | None = None
    # Étiquettes imposées par la source (ex : flux de la BCE -> EUR), complétées par news_filter.
    default_tags: list[str] = field(default_factory=list)


class ProviderError(Exception):
    """Erreur d'un fournisseur externe (réseau, quota, format inattendu)."""


class NewsProvider(ABC):
    name: str = "provider"

    def is_configured(self) -> bool:
        """False si une clé API manque : le provider est alors ignoré (avec un avertissement)."""
        return True

    @abstractmethod
    async def fetch(self, client: httpx.AsyncClient) -> list[RawNews]:
        """Récupère les dernières news au format commun."""


def clean_text(value: str | None) -> str:
    """Supprime les balises HTML et normalise les espaces."""
    if not value:
        return ""
    text = html.unescape(_TAG_RE.sub(" ", value))
    return _SPACE_RE.sub(" ", text).strip()


def short_summary(value: str | None, max_length: int = SUMMARY_MAX_LENGTH) -> str | None:
    """Résumé court uniquement : on ne recopie jamais l'article complet."""
    text = clean_text(value)
    if not text:
        return None
    if len(text) <= max_length:
        return text
    cut = text[: max_length - 1].rsplit(" ", 1)[0]
    return f"{cut}…"
