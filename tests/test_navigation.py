import pytest


@pytest.mark.parametrize("fixture", ["editor_client", "viewer_client"])
@pytest.mark.parametrize("lang", ["pt", "en", "it"])
def test_navigation_permissions_and_preserved_query(request, fixture, lang):
    client = request.getfixturevalue(fixture)
    result = client.get(f"/?month=2026-10&lang={lang}&q=water&status=paid")
    assert result.status_code == 200
    header = result.text.split("<header")[1].split("</header>")[0]
    assert "data-disclosure" in header
    assert "month=2026-10" in header and "q=water" in header and "status=paid" in header
    assert ('href="/docs"' in header) == (fixture == "editor_client")
    assert 'action="/logout" method="post"' in header
    assert "🇧🇷" not in header
    assert "Dashboard</a>" not in header
