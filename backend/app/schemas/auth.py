import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models import AuditLog, User
from app.schemas.common import as_utc
from app.services.auth import EMAIL_RE, normalize_email

PASSWORD_MIN_LENGTH = 8


def _email(value: str) -> str:
    value = normalize_email(value)
    if not EMAIL_RE.match(value):
        raise ValueError("Adresse e-mail invalide.")
    return value


class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)
    full_name: str = Field(min_length=1, max_length=120)

    _check_email = field_validator("email")(_email)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Le nom est obligatoire.")
        return value

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if len(value) < PASSWORD_MIN_LENGTH or not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError(f"Le mot de passe doit contenir au moins {PASSWORD_MIN_LENGTH} caractères, dont une lettre et un chiffre.")
        return value


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)

    _check_email = field_validator("email")(_email)


class GoogleLoginIn(BaseModel):
    credential: str = Field(min_length=20, max_length=4096)


class AuthConfig(BaseModel):
    google_client_id: str | None


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    avatar_url: str | None
    has_password: bool
    google_linked: bool
    created_at: datetime
    last_login_at: datetime | None

    @classmethod
    def from_model(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            has_password=bool(user.password_hash),
            google_linked=bool(user.google_sub),
            created_at=as_utc(user.created_at),
            last_login_at=as_utc(user.last_login_at),
        )


class ActivityOut(BaseModel):
    event: str
    created_at: datetime
    ip: str | None
    user_agent: str | None

    @classmethod
    def from_model(cls, entry: AuditLog) -> "ActivityOut":
        return cls(event=entry.event, created_at=as_utc(entry.created_at), ip=entry.ip, user_agent=entry.user_agent)
