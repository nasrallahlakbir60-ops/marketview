"""Comptes : sessions, connexion Google, journal d'activité et purge des données expirées."""

import re
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from starlette.requests import HTTPConnection

from app.config import get_settings
from app.core.logging import get_logger, request_id_var
from app.core.security import client_ip, hash_token, new_session_token
from app.models import AuditLog, User, UserSession
from app.schemas.common import as_utc

logger = get_logger("app.audit")

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
# Mise à jour de last_seen_at au plus une fois par heure (évite une écriture par requête).
LAST_SEEN_PRECISION = timedelta(hours=1)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_google_keys: jwt.PyJWKClient | None = None


class GoogleTokenError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _user_agent(conn: HTTPConnection) -> str | None:
    value = conn.headers.get("user-agent")
    return value[:255] if value else None


def record(db: Session, event: str, conn: HTTPConnection, user_id: int | None = None, **details: object) -> None:
    """Ajoute une ligne au journal d'activité (validée avec la transaction en cours) et la logue."""
    entry = AuditLog(
        event=event,
        user_id=user_id,
        ip=client_ip(conn),
        user_agent=_user_agent(conn),
        request_id=request_id_var.get() if request_id_var.get() != "-" else None,
        details=details or None,
    )
    db.add(entry)
    logger.info("audit %s", event, extra={"audit_event": event, "user_id": user_id, "ip": entry.ip, **details})


def create_session(db: Session, user: User, conn: HTTPConnection) -> str:
    """Ouvre une session et renvoie le jeton à placer dans le cookie."""
    token = new_session_token()
    now = datetime.now(timezone.utc)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            created_at=now,
            last_seen_at=now,
            expires_at=now + timedelta(days=get_settings().session_days),
            ip=client_ip(conn),
            user_agent=_user_agent(conn),
        )
    )
    user.last_login_at = now
    return token


def user_from_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    now = datetime.now(timezone.utc)
    if session is None or as_utc(session.expires_at) <= now or not session.user.is_active:
        return None
    if now - as_utc(session.last_seen_at) > LAST_SEEN_PRECISION:
        session.last_seen_at = now
        db.commit()
    return session.user


def revoke_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(token)))


def revoke_all_sessions(db: Session, user: User) -> int:
    return db.execute(delete(UserSession).where(UserSession.user_id == user.id)).rowcount or 0


def verify_google_credential(credential: str) -> dict:
    """Vérifie le jeton d'identité renvoyé par le bouton Google (signature, audience, émetteur, expiration)."""
    global _google_keys
    client_id = get_settings().google_client_id
    if not client_id:
        raise GoogleTokenError("Connexion Google non configurée sur le serveur.")
    if _google_keys is None:
        _google_keys = jwt.PyJWKClient(GOOGLE_CERTS_URL, cache_keys=True, lifespan=3600)
    try:
        key = _google_keys.get_signing_key_from_jwt(credential)
        claims = jwt.decode(credential, key.key, algorithms=["RS256"], audience=client_id, issuer=GOOGLE_ISSUERS)
    except jwt.PyJWTError as exc:
        raise GoogleTokenError("Jeton Google invalide ou expiré.") from exc
    if not claims.get("email") or not claims.get("email_verified"):
        raise GoogleTokenError("Adresse e-mail Google non vérifiée.")
    return claims


def purge_expired(db: Session) -> dict[str, int]:
    """Supprime les sessions expirées et le journal d'activité plus ancien que AUDIT_RETENTION_DAYS."""
    now = datetime.now(timezone.utc)
    sessions = db.execute(delete(UserSession).where(UserSession.expires_at <= now)).rowcount or 0
    cutoff = now - timedelta(days=get_settings().audit_retention_days)
    logs = db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff)).rowcount or 0
    db.commit()
    return {"sessions": sessions, "audit_logs": logs}
