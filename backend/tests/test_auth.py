import json
import logging
from datetime import datetime, timedelta, timezone

import pytest
from starlette.websockets import WebSocketDisconnect

from app.api.deps import SESSION_COOKIE
from app.core.logging import JsonFormatter, RequestIdFilter, request_id_var
from app.core.security import hash_token
from app.models import AuditLog, User, UserSession
from app.services import auth
from tests.conftest import TEST_USER


def events(db) -> list[str]:
    db.expire_all()
    return [row.event for row in db.query(AuditLog).order_by(AuditLog.id)]


# --- Accès réservé aux comptes ---------------------------------------------------------

@pytest.mark.parametrize("path", ["/api/pairs", "/api/pairs/EURUSD", "/api/news?pair=EURUSD", "/api/macro?pair=EURUSD",
                                  "/api/calendar?pair=EURUSD", "/api/news/sources", "/api/auth/me"])
def test_data_routes_require_login(anon_client, seeded, path) -> None:
    response = anon_client.get(path)
    assert response.status_code == 401
    assert response.json()["detail"] == "Connexion requise."


def test_public_routes_stay_open(anon_client) -> None:
    assert anon_client.get("/health").status_code == 200
    assert anon_client.get("/api/auth/config").json() == {"google_client_id": None}


def test_websocket_requires_login(anon_client, seeded) -> None:
    with anon_client.websocket_connect("/ws/news/EURUSD") as ws, pytest.raises(WebSocketDisconnect) as closed:
        ws.receive_json()
    assert closed.value.code == 4401


# --- Inscription / connexion -----------------------------------------------------------

def test_register_opens_session_and_stores_only_token_hash(anon_client, seeded) -> None:
    response = anon_client.post("/api/auth/register", json={**TEST_USER, "email": "  Trader@Example.COM "})

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "trader@example.com"
    assert body["has_password"] is True and body["google_linked"] is False
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "samesite=lax" in cookie.lower()

    token = anon_client.cookies[SESSION_COOKIE]
    stored = seeded.query(UserSession).one()
    assert stored.token_hash == hash_token(token) != token
    user = seeded.query(User).one()
    assert user.password_hash.startswith("$argon2id$")
    assert anon_client.get("/api/pairs").status_code == 200
    assert events(seeded) == ["signup"]


@pytest.mark.parametrize("payload, message", [
    ({"password": "court1"}, "au moins 8 caractères"),
    ({"password": "sanschiffre"}, "un chiffre"),
    ({"email": "pas-un-email"}, "Adresse e-mail invalide"),
    ({"full_name": "   "}, "Le nom est obligatoire"),
])
def test_register_validation(anon_client, payload, message) -> None:
    response = anon_client.post("/api/auth/register", json={**TEST_USER, **payload})
    assert response.status_code == 422
    assert message in json.dumps(response.json(), ensure_ascii=False)


def test_register_duplicate_email(client) -> None:
    response = client.post("/api/auth/register", json={**TEST_USER, "email": "TRADER@example.com"})
    assert response.status_code == 409


def test_login_logout_and_failed_attempts_are_audited(client, seeded) -> None:
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401

    bad = client.post("/api/auth/login", json={"email": TEST_USER["email"], "password": "mauvais123"})
    assert bad.status_code == 401
    assert bad.json()["detail"] == "E-mail ou mot de passe incorrect."
    unknown = client.post("/api/auth/login", json={"email": "inconnu@example.com", "password": "mauvais123"})
    assert unknown.json()["detail"] == bad.json()["detail"]  # pas d'indice sur l'existence du compte

    ok = client.post("/api/auth/login", json={"email": "TRADER@example.com", "password": TEST_USER["password"]})
    assert ok.status_code == 200
    assert client.get("/api/auth/me").json()["full_name"] == "Test Trader"

    assert events(seeded) == ["signup", "logout", "login_failed", "login_failed", "login"]
    failed = seeded.query(AuditLog).filter_by(event="login_failed").first()
    assert failed.details == {"email": TEST_USER["email"]}
    assert failed.ip and failed.request_id


def test_expired_session_is_rejected(client, seeded) -> None:
    session = seeded.query(UserSession).one()
    session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    seeded.commit()

    assert client.get("/api/pairs").status_code == 401


def test_logout_all_closes_every_session(client, anon_client, seeded) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as other_device:
        other_device.post("/api/auth/login", json={"email": TEST_USER["email"], "password": TEST_USER["password"]})
        assert seeded.query(UserSession).count() == 2

        assert client.post("/api/auth/logout-all").status_code == 204

        assert other_device.get("/api/auth/me").status_code == 401
    assert seeded.query(UserSession).count() == 0


def test_login_is_rate_limited(anon_client, settings, monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 3)
    codes = [anon_client.post("/api/auth/login", json={"email": "a@b.co", "password": "x1234567"}).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]


# --- Google ------------------------------------------------------------------------------

GOOGLE_CLAIMS = {"sub": "google-123", "email": "Trader@Example.com", "email_verified": True,
                 "name": "Trader Google", "picture": "https://lh3.googleusercontent.com/a/photo"}


def test_google_without_client_id_is_refused(anon_client, seeded) -> None:
    response = anon_client.post("/api/auth/google", json={"credential": "x" * 40})
    assert response.status_code == 401
    assert "non configurée" in response.json()["detail"]


def test_google_signup_then_login(anon_client, seeded, monkeypatch) -> None:
    monkeypatch.setattr(auth, "verify_google_credential", lambda credential: GOOGLE_CLAIMS)

    first = anon_client.post("/api/auth/google", json={"credential": "x" * 40}).json()
    assert first["email"] == "trader@example.com"
    assert first["google_linked"] is True and first["has_password"] is False
    assert first["avatar_url"] == GOOGLE_CLAIMS["picture"]

    anon_client.post("/api/auth/logout")
    anon_client.post("/api/auth/google", json={"credential": "x" * 40})

    assert seeded.query(User).count() == 1
    assert events(seeded) == ["signup", "logout", "login"]
    # Pas de mot de passe : la connexion par e-mail reste impossible.
    assert anon_client.post("/api/auth/login", json={"email": "trader@example.com", "password": "nimporte1"}).status_code == 401


def test_google_links_existing_email_account(client, seeded, monkeypatch) -> None:
    monkeypatch.setattr(auth, "verify_google_credential", lambda credential: GOOGLE_CLAIMS)
    client.post("/api/auth/logout")

    body = client.post("/api/auth/google", json={"credential": "x" * 40}).json()

    assert body["has_password"] is True and body["google_linked"] is True
    assert body["full_name"] == "Test Trader"  # le nom choisi à l'inscription est conservé
    assert seeded.query(User).count() == 1


# --- Données personnelles ----------------------------------------------------------------

def test_activity_and_export(client) -> None:
    activity = client.get("/api/auth/me/activity").json()
    assert [entry["event"] for entry in activity] == ["signup"]

    export = client.get("/api/auth/me/export").json()
    assert export["account"]["email"] == TEST_USER["email"]
    assert len(export["sessions"]) == 1
    assert [entry["event"] for entry in export["activity"]] == ["signup"]


def test_delete_account_keeps_anonymous_audit_trail(client, seeded) -> None:
    user_id = seeded.query(User).one().id

    assert client.delete("/api/auth/me").status_code == 204

    seeded.expire_all()
    assert seeded.query(User).count() == 0
    assert seeded.query(UserSession).count() == 0
    assert {row.user_id for row in seeded.query(AuditLog)} == {None}
    deleted = seeded.query(AuditLog).filter_by(event="account_deleted").one()
    assert deleted.details == {"deleted_user_id": user_id}
    assert client.get("/api/pairs").status_code == 401


def test_purge_expired(client, seeded, settings, monkeypatch) -> None:
    monkeypatch.setattr(settings, "audit_retention_days", 30)
    seeded.query(UserSession).one().expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    seeded.add(AuditLog(event="login", created_at=datetime.now(timezone.utc) - timedelta(days=31)))
    seeded.commit()

    assert auth.purge_expired(seeded) == {"sessions": 1, "audit_logs": 1}
    assert events(seeded) == ["signup"]


# --- Logs ----------------------------------------------------------------------------------

def test_responses_carry_request_id(client) -> None:
    generated = client.get("/api/auth/me").headers["X-Request-ID"]
    assert len(generated) == 32
    assert client.get("/api/auth/me", headers={"X-Request-ID": "abc-12345"}).headers["X-Request-ID"] == "abc-12345"
    assert client.get("/api/auth/me", headers={"X-Request-ID": "bad id\n"}).headers["X-Request-ID"] != "bad id\n"


def test_json_log_format() -> None:
    record = logging.LogRecord("app.access", logging.INFO, __file__, 1, "GET %s", ("/api/pairs",), None)
    record.http_status = 200
    record.user_id = 7
    token = request_id_var.set("req-1")
    try:
        RequestIdFilter().filter(record)
    finally:
        request_id_var.reset(token)

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "GET /api/pairs"
    assert payload["level"] == "INFO"
    assert payload["request_id"] == "req-1"
    assert payload["http_status"] == 200 and payload["user_id"] == 7
    assert payload["timestamp"].endswith("+00:00")


def test_verify_google_credential_checks_signature_and_audience(settings, monkeypatch) -> None:
    import time

    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class FakeKeys:
        def get_signing_key_from_jwt(self, token):
            return type("Key", (), {"key": key.public_key()})()

    monkeypatch.setattr(settings, "google_client_id", "my-client.apps.googleusercontent.com")
    monkeypatch.setattr(auth, "_google_keys", FakeKeys())

    def token(**overrides) -> str:
        claims = {"iss": "https://accounts.google.com", "aud": "my-client.apps.googleusercontent.com", "sub": "1",
                  "email": "a@b.com", "email_verified": True, "exp": int(time.time()) + 300, **overrides}
        return jwt.encode(claims, key, algorithm="RS256")

    assert auth.verify_google_credential(token())["sub"] == "1"
    for bad in (token(aud="autre-site"), token(iss="https://evil.example"), token(exp=int(time.time()) - 10)):
        with pytest.raises(auth.GoogleTokenError, match="invalide"):
            auth.verify_google_credential(bad)
    with pytest.raises(auth.GoogleTokenError, match="non vérifiée"):
        auth.verify_google_credential(token(email_verified=False))
