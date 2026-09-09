"""Retired accounts cannot authenticate or reuse old signed cookies."""

import base64
import hashlib
import hmac

import pytest
from pydantic import ValidationError

from app.auth import (
    AuthenticatedUser,
    Role,
    authenticate_credentials,
    create_session_token,
    user_from_session,
)
from app.config import Settings, settings


@pytest.mark.parametrize(
    "name,role,password",
    [("editor", "editor", "admin"), ("viewer", "viewer", "client")],
)
def test_retired_aliases_and_signed_sessions(unauth_client, name, role, password):
    secret = settings.admin_pass if password == "admin" else settings.client_pass
    assert authenticate_credentials(name, secret) is None
    assert unauth_client.get("/commitments", auth=(name, secret)).status_code == 401
    assert (
        unauth_client.post(
            "/login", data={"role": role, "password": secret}
        ).status_code
        == 401
    )
    # Old cookies used public or legacy usernames but always retired role values.
    for username in [name, password]:
        payload = f"{username}:{role}"
        sig = hmac.new(
            settings.session_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        token = base64.urlsafe_b64encode(f"{payload}:{sig}".encode()).decode()
        assert user_from_session(token) is None
        unauth_client.cookies.set("privio_session", token)
        assert unauth_client.get("/", follow_redirects=False).status_code == 303
    unauth_client.cookies.clear()


def test_cookie_username_must_match_role():
    token = create_session_token(AuthenticatedUser("retired-name", Role.ADMIN))
    assert user_from_session(token) is None
    token = create_session_token(AuthenticatedUser(settings.client_user, Role.ADMIN))
    assert user_from_session(token) is None
    assert authenticate_credentials("inválido", "não") is None


def test_production_requires_explicit_new_secrets():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production")
    config = Settings(
        _env_file=None,
        environment="production",
        admin_pass="test-explicit-admin",
        client_pass="test-explicit-client",
        session_secret="test-explicit-session",
    )
    assert config.admin_user == "admin" and config.client_user == "client"
    for changes in [
        {"admin_user": "client"},
        {"admin_pass": ""},
        {"client_user": "bad:name"},
    ]:
        with pytest.raises(ValidationError):
            Settings(
                _env_file=None,
                admin_user=changes.get("admin_user", "admin"),
                admin_pass=changes.get("admin_pass", "admin123"),
                client_user=changes.get("client_user", "client"),
            )


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/ui/commitments"),
        ("post", "/ui/commitments/1/edit"),
        ("post", "/ui/payments"),
        ("post", "/ui/accounts"),
        ("post", "/ui/transfers"),
        ("post", "/ui/income/1/receive"),
        ("delete", "/ui/commitments/1/occurrences/2026-09-10"),
    ],
)
def test_client_web_writes_stay_forbidden(readonly_client, method, path):
    assert getattr(readonly_client, method)(path).status_code == 403
