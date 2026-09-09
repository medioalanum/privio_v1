"""Canonical roles preserve authorization and reject retired logins/sessions."""

import pytest

from app.auth import (
    Role,
    authenticate_credentials,
    create_session_token,
    user_from_session,
)
from app.config import settings


@pytest.mark.parametrize(
    "name,password,role",
    [
        (settings.admin_user, settings.admin_pass, Role.ADMIN),
        (settings.client_user, settings.client_pass, Role.CLIENT),
    ],
)
def test_login_names_and_sessions(name, password, role):
    user = authenticate_credentials(name, password)
    assert user is not None and user.role == role
    restored = user_from_session(create_session_token(user))
    assert restored is not None and restored.role == role
    assert authenticate_credentials(name, password + "wrong") is None


def test_role_labels(admin_client, readonly_client):
    assert ">Admin</span>" in admin_client.get("/").text
    assert ">Client</span>" in readonly_client.get("/").text


def test_client_cannot_write(unauth_client):
    response = unauth_client.post(
        "/commitments", auth=("client", settings.client_pass), json={}
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "role,password,label",
    [
        ("admin", settings.admin_pass, "Admin"),
        ("client", settings.client_pass, "Client"),
    ],
)
def test_browser_login_names(unauth_client, role, password, label):
    login = unauth_client.get("/login")
    assert '<option value="admin" selected>Admin</option>' in login.text
    assert '<option value="client">Client</option>' in login.text
    response = unauth_client.post("/login", data={"role": role, "password": password})
    assert response.status_code == 200
    assert f">{label}</span>" in response.text


def test_demo_notice_is_opt_in(unauth_client, monkeypatch):
    assert "Demonstração local" not in unauth_client.get("/login").text
    monkeypatch.setattr(settings, "preview_mode", True)
    assert "Demonstração local" in unauth_client.get("/login").text
