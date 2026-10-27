"""État des sources externes affiché par le frontend ("Source non configurée", erreurs d'accès...)."""

from app.schemas.news import SourceStatus
from app.services import cache

NOT_CONFIGURED = "Source non configurée"
ERROR_TTL = 24 * 3600


def _key(name: str) -> str:
    return f"source:error:{name}"


def record_error(name: str, message: str) -> None:
    cache.set_json(_key(name), message, ERROR_TTL)


def clear_error(name: str) -> None:
    cache.delete_pattern(_key(name))


def status(name: str, configured: bool, env_var: str | None = None) -> SourceStatus:
    if not configured:
        hint = f" ({env_var} absente du .env)" if env_var else ""
        return SourceStatus(name=name, configured=False, message=f"{NOT_CONFIGURED}{hint}")
    error = cache.get_json(_key(name))
    return SourceStatus(name=name, configured=True, message=error if isinstance(error, str) else None)
