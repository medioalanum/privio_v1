"""Automated tests for HTTP Basic Auth RBAC and i18n translations."""

import base64

from fastapi.testclient import TestClient


def test_auth_unauthenticated_and_invalid(unauth_client: TestClient) -> None:
    """Test 401 Unauthorized when unauthenticated or providing invalid credentials."""
    # 1. No credentials
    res = unauth_client.get("/commitments")
    assert res.status_code == 401
    assert "WWW-Authenticate" in res.headers

    # 2. Invalid credentials
    bad_auth = {"Authorization": "Basic " + base64.b64encode(b"wrong:creds").decode()}
    res_bad = unauth_client.get("/commitments", headers=bad_auth)
    assert res_bad.status_code == 401


def test_branded_login_and_session_flow(unauth_client: TestClient) -> None:
    """Anonymous browser users see login and can establish a cookie session."""
    anonymous = unauth_client.get("/", follow_redirects=False)
    assert anonymous.status_code == 303
    assert anonymous.headers["location"].startswith("/login")

    page = unauth_client.get("/login")
    assert page.status_code == 200
    assert "Bem-vindo de volta" in page.text
    assert 'name="role"' in page.text
    assert 'value="editor"' in page.text
    assert 'value="viewer"' in page.text

    invalid = unauth_client.post("/login", data={"role": "editor", "password": "wrong"})
    assert invalid.status_code == 401
    assert "Usuário ou senha incorretos" in invalid.text

    logged_in = unauth_client.post(
        "/login",
        data={"role": "editor", "password": "editor123"},
        follow_redirects=False,
    )
    assert logged_in.status_code == 303
    assert "privio_session" in logged_in.cookies

    dashboard = unauth_client.get("/")
    assert dashboard.status_code == 200
    assert "Privio" in dashboard.text

    logged_out = unauth_client.post("/logout", follow_redirects=False)
    assert logged_out.status_code == 303


def test_auth_viewer_role_permissions(
    viewer_client: TestClient, editor_client: TestClient
) -> None:
    """Test that Viewer role can read data but cannot mutate (403 Forbidden)."""
    # Create a commitment with editor
    create_res = editor_client.post(
        "/commitments",
        json={
            "description": "Office Supplies",
            "amount": "100.00",
            "due_date": "2026-09-01",
            "category": "Office",
        },
    )
    assert create_res.status_code == 201
    item_id = create_res.json()["id"]

    # Viewer can read commitments, upcoming, suggested-monthly, reserve-balance, deposits, dashboard
    assert viewer_client.get("/commitments").status_code == 200
    assert viewer_client.get(f"/commitments/{item_id}").status_code == 200
    assert viewer_client.get("/upcoming?days=30").status_code == 200
    assert viewer_client.get("/suggested-monthly").status_code == 200
    assert viewer_client.get("/deposits").status_code == 200
    assert viewer_client.get("/reserve-balance").status_code == 200
    assert viewer_client.get("/").status_code == 200
    assert viewer_client.get("/ui/upcoming?days=30").status_code == 200

    # Viewer CANNOT create commitment (403)
    res_post = viewer_client.post(
        "/commitments",
        json={
            "description": "Forbidden Create",
            "amount": "50.00",
            "due_date": "2026-09-01",
            "category": "Test",
        },
    )
    assert res_post.status_code == 403
    assert "Editor role required" in res_post.json()["detail"]

    # Viewer CANNOT update commitment (403)
    res_put = viewer_client.put(
        f"/commitments/{item_id}",
        json={
            "description": "Forbidden Update",
            "amount": "120.00",
            "due_date": "2026-09-01",
            "category": "Office",
        },
    )
    assert res_put.status_code == 403

    # Viewer CANNOT patch commitment (403)
    res_patch = viewer_client.patch(
        f"/commitments/{item_id}",
        json={"amount": "130.00"},
    )
    assert res_patch.status_code == 403

    # Viewer CANNOT delete commitment (403)
    res_del = viewer_client.delete(f"/commitments/{item_id}")
    assert res_del.status_code == 403

    # Viewer CANNOT create deposit (403)
    res_dep = viewer_client.post(
        "/deposits",
        json={"amount": "500.00", "date": "2026-09-01"},
    )
    assert res_dep.status_code == 403


def test_auth_editor_role_full_access(editor_client: TestClient) -> None:
    """Test that Editor role has full access to create, read, update, and delete."""
    # Create
    create_res = editor_client.post(
        "/commitments",
        json={
            "description": "Hosting Server",
            "amount": "45.00",
            "due_date": "2026-09-01",
            "category": "Tech",
        },
    )
    assert create_res.status_code == 201
    item_id = create_res.json()["id"]

    # Update
    put_res = editor_client.put(
        f"/commitments/{item_id}",
        json={
            "description": "Hosting Server Updated",
            "amount": "50.00",
            "due_date": "2026-09-01",
            "category": "Tech",
        },
    )
    assert put_res.status_code == 200

    # Delete
    del_res = editor_client.delete(f"/commitments/{item_id}")
    assert del_res.status_code == 204


def test_i18n_dashboard_and_partials(viewer_client: TestClient) -> None:
    """Test dictionary-based i18n support for pt, en, and it."""
    # 1. Portuguese (default)
    res_pt = viewer_client.get("/?lang=pt")
    assert res_pt.status_code == 200
    assert "Recebido no Mês" in res_pt.text
    assert "Saldo Projetado" in res_pt.text
    assert "Próximos Vencimentos" in res_pt.text
    assert "Todos os Compromissos" in res_pt.text
    assert "Privio © 2026 — Todos os direitos reservados." in res_pt.text

    # 2. English
    res_en = viewer_client.get("/?lang=en")
    assert res_en.status_code == 200
    assert "Received This Month" in res_en.text
    assert "Projected Balance" in res_en.text
    assert "Upcoming Due Dates" in res_en.text
    assert "All Commitments" in res_en.text
    assert "Privio © 2026 — All rights reserved." in res_en.text

    # 3. Italian
    res_it = viewer_client.get("/?lang=it")
    assert res_it.status_code == 200
    assert "Ricevuto nel Mese" in res_it.text
    assert "Saldo Previsto" in res_it.text
    assert "Prossime Scadenze" in res_it.text
    assert "Tutti gli Impegni" in res_it.text
    assert "Privio © 2026 — Tutti i diritti riservati." in res_it.text

    # 4. Partial upcoming table with i18n
    partial_en = viewer_client.get("/ui/upcoming?days=30&lang=en")
    assert partial_en.status_code == 200
    assert "30 days" in partial_en.text
    assert "Due Date" in partial_en.text

    partial_it = viewer_client.get("/ui/upcoming?days=60&lang=it")
    assert partial_it.status_code == 200
    assert "60 giorni" in partial_it.text
    assert "Data Prevista" in partial_it.text

    # 5. Unsupported language falls back to Portuguese
    res_fallback = viewer_client.get("/?lang=fr")
    assert res_fallback.status_code == 200
    assert "Recebido no Mês" in res_fallback.text
