from datetime import datetime, timezone


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite renvoie des dates naïves : on les considère comme UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
