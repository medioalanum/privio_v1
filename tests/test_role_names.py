"""Public role names preserve authorization and existing signed sessions."""

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
        ("admin", settings.editor_pass, Role.EDITOR),
        ("client", settings.viewer_pass, Role.VIEWER),
        (settings.editor_user, settings.editor_pass, Role.EDITOR),
        (settings.viewer_user, settings.viewer_pass, Role.VIEWER),
    ],
)
def test_login_names_and_sessions(name, password, role):
    user = authenticate_credentials(name, password)
    assert user is not None and user.role == role
    restored = user_from_session(create_session_token(user))
    assert restored is not None and restored.role == role
    assert authenticate_credentials(name, password + "wrong") is None


def test_role_labels(editor_client, viewer_client):
    assert ">Admin</span>" in editor_client.get("/").text
    assert ">Client</span>" in viewer_client.get("/").text


def test_client_alias_cannot_write(unauth_client):
    response = unauth_client.post(
        "/commitments", auth=("client", settings.viewer_pass), json={}
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "role,password,label",
    [
        ("admin", settings.editor_pass, "Admin"),
        ("client", settings.viewer_pass, "Client"),
    ],
)
def test_browser_login_names(unauth_client, role, password, label):
    login = unauth_client.get("/login")
    assert '<option value="admin">Admin</option>' in login.text
    assert '<option value="client">Client</option>' in login.text
    response = unauth_client.post("/login", data={"role": role, "password": password})
    assert response.status_code == 200
    assert f">{label}</span>" in response.text


def test_demo_notice_is_opt_in(unauth_client, monkeypatch):
    assert "Demonstração local" not in unauth_client.get("/login").text
    monkeypatch.setattr(settings, "preview_mode", True)
    assert "Demonstração local" in unauth_client.get("/login").text
