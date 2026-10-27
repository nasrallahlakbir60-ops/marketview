"""Petit cache JSON dans Redis. Toute erreur Redis est absorbée : sans Redis, on lit simplement la BDD."""

import json
import time
from typing import Any

import redis

from app.core.logging import get_logger
from app.redis_client import ensure_available, get_redis, mark_down

logger = get_logger(__name__)

NEWS_TTL = 60
MACRO_TTL = 24 * 3600
CALENDAR_TTL = 3600

REDIS_ERRORS = (redis.RedisError, OSError)

_last_warning = 0.0


def report_error(exc: Exception) -> None:
    """Ouvre le disjoncteur Redis et logue un avertissement (au plus une fois par minute)."""
    global _last_warning
    mark_down()
    now = time.monotonic()
    if now - _last_warning > 60:
        logger.warning("Redis indisponible, cache ignoré : %s", exc)
        _last_warning = now


def client() -> redis.Redis:
    ensure_available()
    return get_redis()


def get_json(key: str) -> Any | None:
    try:
        raw = client().get(key)
    except REDIS_ERRORS as exc:
        report_error(exc)
        return None
    return json.loads(raw) if raw else None


def set_json(key: str, value: Any, ttl: int) -> None:
    try:
        client().set(key, json.dumps(value, default=str), ex=ttl)
    except REDIS_ERRORS as exc:
        report_error(exc)


def delete_pattern(pattern: str) -> None:
    try:
        redis_client = client()
        keys = list(redis_client.scan_iter(match=pattern, count=500))
        if keys:
            redis_client.delete(*keys)
    except REDIS_ERRORS as exc:
        report_error(exc)


def acquire_lock(key: str, ttl: int) -> bool:
    """Verrou "une seule exécution par période" (SET NX EX). Sans Redis, on exécute quand même."""
    try:
        return bool(client().set(key, "1", nx=True, ex=ttl))
    except REDIS_ERRORS as exc:
        report_error(exc)
        return True


def release_lock(key: str) -> None:
    try:
        client().delete(key)
    except REDIS_ERRORS as exc:
        report_error(exc)


def publish(channel: str, message: str) -> bool:
    try:
        client().publish(channel, message)
        return True
    except REDIS_ERRORS as exc:
        report_error(exc)
        return False
