"""Limitation du nombre de requêtes par IP (fenêtre fixe d'une minute).

Compteur partagé dans Redis (fonctionne avec plusieurs workers gunicorn) ;
repli en mémoire si Redis est indisponible.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.core.security import client_ip
from app.services import cache

WINDOW_SECONDS = 60
_memory_counters: dict[str, int] = defaultdict(int)


def _hit(key: str) -> int:
    try:
        pipe = cache.client().pipeline()
        pipe.incr(key)
        pipe.expire(key, WINDOW_SECONDS)
        count, _ = pipe.execute()
        return int(count)
    except cache.REDIS_ERRORS as exc:
        cache.report_error(exc)
        if len(_memory_counters) > 10_000:
            _memory_counters.clear()
        _memory_counters[key] += 1
        return _memory_counters[key]


def _enforce(request: Request, scope: str, limit: int) -> None:
    if limit <= 0:
        return
    bucket = int(time.time() // WINDOW_SECONDS)
    count = _hit(f"{scope}:{client_ip(request)}:{bucket}")
    if count > limit:
        retry_after = WINDOW_SECONDS - int(time.time()) % WINDOW_SECONDS
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de requêtes, réessayez dans un instant.",
            headers={"Retry-After": str(retry_after)},
        )


def rate_limit(request: Request) -> None:
    """Dépendance FastAPI à ajouter sur les routeurs publics."""
    _enforce(request, "rl", get_settings().rate_limit_per_minute)


def auth_rate_limit(request: Request) -> None:
    """Limite plus stricte sur inscription / connexion (anti force brute sur les mots de passe)."""
    _enforce(request, "rl-auth", get_settings().auth_rate_limit_per_minute)
