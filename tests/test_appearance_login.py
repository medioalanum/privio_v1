import pytest


@pytest.mark.parametrize(
    "lang,title",
    [
        ("pt", "Suas contas, com clareza."),
        ("en", "Your bills, clearly."),
        ("it", "Le tue spese, in chiaro."),
    ],
)
def test_login_language_theme_and_error(unauth_client, lang, title):
    result = unauth_client.get("/login?lang=" + lang)
    assert title in result.text
    assert f'<html lang="{lang}" data-theme="dark">' in result.text
    assert 'data-theme="dark"' in result.text
    assert 'class="site-menu"' not in result.text
    assert "data-theme-choice" not in result.text
    assert "localStorage" not in result.text
    assert 'class="language-picker"' in result.text
    assert 'autocomplete="current-password"' in result.text
    assert 'aria-controls="password"' in result.text
    error = unauth_client.post(
        "/login?lang=" + lang,
        data={"role": "client", "password": "not-a-password", "next_path": "/"},
    )
    assert error.status_code == 401
    assert '<option value="client" selected>' in error.text
    assert 'role="alert"' in error.text
    assert 'value="not-a-password"' not in error.text


def test_login_preserves_language(unauth_client):
    from app.config import settings

    result = unauth_client.post(
        "/login?lang=it",
        data={"role": "admin", "password": settings.admin_pass, "next_path": "/"},
        follow_redirects=False,
    )
    assert result.status_code == 303 and result.headers["location"] == "/?lang=it"
