"""Dépendances d'authentification : tout le site (sauf /api/auth, /health et le cron) exige une session."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.requests import HTTPConnection

from app.database import SessionLocal, get_db
from app.models import User
from app.services import auth

SESSION_COOKIE = "mv_session"


def current_user(conn: HTTPConnection, db: Session = Depends(get_db)) -> User | None:
    user = auth.user_from_token(db, conn.cookies.get(SESSION_COOKIE))
    if user is not None:
        conn.state.user_id = user.id  # repris par le log de la requête
    return user


def require_user(user: User | None = Depends(current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Connexion requise.")
    return user


def websocket_user_id(conn: HTTPConnection) -> int | None:
    """Version WebSocket (session BDD courte : la connexion peut rester ouverte des heures)."""
    with SessionLocal() as db:
        user = auth.user_from_token(db, conn.cookies.get(SESSION_COOKIE))
        return user.id if user else None
