"""Comptes utilisateurs : inscription, connexion (e-mail ou Google), déconnexion, données personnelles.

La session est un jeton aléatoire dans un cookie httpOnly (illisible par le JavaScript de la page) ;
la base n'en garde que le hash. Chaque événement sensible est inscrit dans le journal d'activité.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, require_user
from app.config import get_settings
from app.core.rate_limit import auth_rate_limit, rate_limit
from app.core.security import hash_password, password_needs_rehash, verify_password
from app.database import get_db
from app.models import AuditLog, User, UserSession
from app.schemas.auth import ActivityOut, AuthConfig, GoogleLoginIn, LoginIn, RegisterIn, UserOut
from app.schemas.common import as_utc
from app.services import auth
from app.services.serverless import ensure_database

router = APIRouter(prefix="/api/auth", tags=["auth"], dependencies=[Depends(rate_limit), Depends(ensure_database)])

INVALID_CREDENTIALS = "E-mail ou mot de passe incorrect."
ACTIVITY_LIMIT = 20


def _open_session(response: Response, db: Session, user: User, request: Request) -> UserOut:
    token = auth.create_session(db, user, request)
    db.commit()
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_days * 24 * 3600,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    request.state.user_id = user.id
    return UserOut.from_model(user)


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=get_settings().secure_cookies, samesite="lax")


@router.get("/config", response_model=AuthConfig)
def auth_config() -> AuthConfig:
    """Paramètres publics du formulaire de connexion (bouton Google affiché si configuré)."""
    return AuthConfig(google_client_id=get_settings().google_client_id or None)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(auth_rate_limit)])
def register(payload: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)) -> UserOut:
    if db.scalar(select(User.id).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un compte existe déjà avec cette adresse e-mail.")
    user = User(email=payload.email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:  # inscription simultanée avec la même adresse
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un compte existe déjà avec cette adresse e-mail.") from exc
    auth.record(db, "signup", request, user.id, method="password")
    return _open_session(response, db, user, request)


@router.post("/login", response_model=UserOut, dependencies=[Depends(auth_rate_limit)])
def login(payload: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        auth.record(db, "login_failed", request, user.id if user else None, email=payload.email)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    auth.record(db, "login", request, user.id, method="password")
    return _open_session(response, db, user, request)


@router.post("/google", response_model=UserOut, dependencies=[Depends(auth_rate_limit)])
def google_login(payload: GoogleLoginIn, request: Request, response: Response, db: Session = Depends(get_db)) -> UserOut:
    try:
        claims = auth.verify_google_credential(payload.credential)
    except auth.GoogleTokenError as exc:
        auth.record(db, "login_failed", request, method="google", reason=str(exc))
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    email = auth.normalize_email(claims["email"])
    user = db.scalar(select(User).where(User.google_sub == claims["sub"]))
    event = "login"
    if user is None:
        # Même adresse qu'un compte e-mail existant : Google a vérifié l'adresse, on relie les deux.
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, full_name=(claims.get("name") or email.split("@")[0])[:120], is_active=True)
            db.add(user)
            event = "signup"
        user.google_sub = claims["sub"]
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ce compte est désactivé.")
    user.avatar_url = claims.get("picture") or user.avatar_url
    db.flush()
    auth.record(db, event, request, user.id, method="google")
    return _open_session(response, db, user, request)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    user = auth.user_from_token(db, token)
    auth.revoke_session(db, token)
    if user is not None:
        auth.record(db, "logout", request, user.id)
    db.commit()
    _clear_cookie(response)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_everywhere(request: Request, response: Response, user: User = Depends(require_user), db: Session = Depends(get_db)) -> None:
    """Ferme toutes les sessions du compte (tous les appareils)."""
    count = auth.revoke_all_sessions(db, user)
    auth.record(db, "logout_all", request, user.id, sessions=count)
    db.commit()
    _clear_cookie(response)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(require_user)) -> UserOut:
    return UserOut.from_model(user)


@router.get("/me/activity", response_model=list[ActivityOut])
def my_activity(user: User = Depends(require_user), db: Session = Depends(get_db)) -> list[ActivityOut]:
    """Dernières connexions et actions du compte."""
    rows = db.scalars(
        select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(ACTIVITY_LIMIT)
    )
    return [ActivityOut.from_model(row) for row in rows]


@router.get("/me/export")
def export_my_data(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)) -> dict:
    """Toutes les données personnelles du compte (droit d'accès / portabilité RGPD)."""
    sessions = db.scalars(select(UserSession).where(UserSession.user_id == user.id).order_by(UserSession.created_at))
    activity = db.scalars(select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.created_at))
    auth.record(db, "data_export", request, user.id)
    db.commit()
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "account": UserOut.from_model(user).model_dump(mode="json"),
        "sessions": [
            {"created_at": as_utc(row.created_at).isoformat(), "expires_at": as_utc(row.expires_at).isoformat(),
             "last_seen_at": as_utc(row.last_seen_at).isoformat(), "ip": row.ip, "user_agent": row.user_agent}
            for row in sessions
        ],
        "activity": [ActivityOut.from_model(row).model_dump(mode="json") for row in activity],
    }


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(request: Request, response: Response, user: User = Depends(require_user), db: Session = Depends(get_db)) -> None:
    """Supprime le compte et ses sessions. Le journal d'activité est conservé, détaché du compte."""
    # Équivalent du ON DELETE SET NULL, aussi sur SQLite (clés étrangères non appliquées par défaut).
    db.execute(update(AuditLog).where(AuditLog.user_id == user.id).values(user_id=None))
    auth.record(db, "account_deleted", request, None, deleted_user_id=user.id)
    auth.revoke_all_sessions(db, user)
    db.delete(user)
    db.commit()
    _clear_cookie(response)
