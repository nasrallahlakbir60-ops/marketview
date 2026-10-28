"""Configuration centralisée des logs.

- Format texte (dev) ou JSON, une ligne par log (production : Vercel, Datadog, Loki... les indexent tels quels).
- Chaque log d'une requête HTTP porte son identifiant (request_id), aussi renvoyé dans l'en-tête X-Request-ID.
- Fichier optionnel avec rotation (LOG_FILE), pour les hébergements avec disque persistant (docker).
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

_FORMAT = "%(asctime)s %(levelname)-8s %(name)s [%(request_id)s]: %(message)s"
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024
LOG_FILE_BACKUPS = 5

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")
# Attributs standard d'un LogRecord : tout le reste vient de `extra=` et part dans le JSON.
_RESERVED = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "request_id"}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        payload.update({key: value for key, value in vars(record).items() if key not in _RESERVED})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO", json_format: bool = False, log_file: str = "") -> None:
    root = logging.getLogger()
    if getattr(root, "_marketview_configured", False):
        root.setLevel(level.upper())
        return
    formatter = JsonFormatter() if json_format else logging.Formatter(_FORMAT)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(RotatingFileHandler(log_file, maxBytes=LOG_FILE_MAX_BYTES, backupCount=LOG_FILE_BACKUPS, encoding="utf-8"))
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(RequestIdFilter())
    root.handlers = handlers
    root.setLevel(level.upper())
    # Les librairies HTTP sont trop bavardes en INFO (elles loguent chaque URL, clés comprises).
    # uvicorn.access est remplacé par le log de requête de l'application (avec durée et utilisateur).
    for noisy in ("httpx", "httpcore", "apscheduler.executors.default", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    root._marketview_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
