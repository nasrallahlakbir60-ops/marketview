"""Mots de passe (Argon2id), jetons de session et adresse IP du client."""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from starlette.requests import HTTPConnection

from app.config import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash stocké en base : une fuite de la table ne permet pas de se connecter."""
    return hashlib.sha256(token.encode()).hexdigest()


def client_ip(conn: HTTPConnection) -> str:
    # Sur Vercel, request.client est le proxy : la vraie IP est dans les en-têtes posés par Vercel (fiables).
    if get_settings().on_vercel:
        forwarded = conn.headers.get("x-real-ip") or conn.headers.get("x-forwarded-for", "").split(",")[0]
        if forwarded.strip():
            return forwarded.strip()
    return conn.client.host if conn.client else "unknown"
