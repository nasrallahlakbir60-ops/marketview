"""Limitation du nombre de requêtes par IP (fenêtre fixe d'une minute).

Compteur partagé dans Redis (fonctionne avec plusieurs workers gunicorn) ;
repli en mémoire si Redis est indisponible.
"""

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.services import cache

WINDOW_SECONDS = 60
_memory_counters: dict[str, int] = defaultdict(int)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


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


def rate_limit(request: Request) -> None:
    """Dépendance FastAPI à ajouter sur les routeurs publics."""
    limit = get_settings().rate_limit_per_minute
    if limit <= 0:
        return
    bucket = int(time.time() // WINDOW_SECONDS)
    count = _hit(f"rl:{_client_ip(request)}:{bucket}")
    if count > limit:
        retry_after = WINDOW_SECONDS - int(time.time()) % WINDOW_SECONDS
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de requêtes, réessayez dans un instant.",
            headers={"Retry-After": str(retry_after)},
        )
