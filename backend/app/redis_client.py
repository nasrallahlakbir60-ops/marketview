"""Clients Redis (synchrone pour le cache, asynchrone pour le Pub/Sub du WebSocket).

Redis est utile mais pas indispensable : si le serveur est injoignable,
les appels échouent proprement et l'application continue sans cache.
"""

import time

import redis
import redis.asyncio as aioredis

from app.config import get_settings

NEWS_CHANNEL = "news:new"
RETRY_AFTER_SECONDS = 30

_sync_client: redis.Redis | None = None
_async_client: aioredis.Redis | None = None
_down_until = 0.0


class RedisUnavailable(redis.ConnectionError):
    """Levée sans tentative réseau tant que le disjoncteur est ouvert."""


def mark_down() -> None:
    global _down_until
    _down_until = time.monotonic() + RETRY_AFTER_SECONDS


def ensure_available() -> None:
    if time.monotonic() < _down_until:
        raise RedisUnavailable("Redis marqué indisponible, nouvel essai dans quelques secondes")


def get_redis() -> redis.Redis:
    global _sync_client
    if _sync_client is None:
        _sync_client = redis.Redis.from_url(
            get_settings().redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )
    return _sync_client


def get_async_redis() -> aioredis.Redis:
    global _async_client
    if _async_client is None:
        _async_client = aioredis.Redis.from_url(
            get_settings().redis_url, decode_responses=True, socket_connect_timeout=2
        )
    return _async_client


def set_clients(sync_client: redis.Redis | None, async_client: aioredis.Redis | None) -> None:
    """Remplace les clients (utilisé par les tests avec fakeredis)."""
    global _sync_client, _async_client, _down_until
    _sync_client, _async_client = sync_client, async_client
    _down_until = 0.0
