"""Automated tests for Jinja2 server-rendered web pages and HTMX endpoints."""

from fastapi.testclient import TestClient


def test_dashboard_page_render(client: TestClient) -> None:
    """Test dashboard index page rendering."""
    # Seed a commitment and deposit
    client.post(
        "/commitments",
        json={
            "description": "Internet Fiber",
            "amount": "120.00",
            "due_date": "2026-09-01",
            "recurrence": "monthly",
            "category": "Utilities",
            "status": "pending",
        },
    )
    client.post(
        "/deposits",
        json={
            "amount": "500.00",
            "date": "2026-09-01",
            "note": "Initial fund",
        },
    )

    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Privio" in response.text
    assert "Total Sugerido do Mês" in response.text
    assert "Saldo de Reserva" in response.text
    assert "Internet Fiber" in response.text
    assert (
        "R$ 120.00" in response.text
        or "R$ 120,00" in response.text
        or "120.00" in response.text
    )


def test_ui_upcoming_partial(client: TestClient) -> None:
    """Test HTMX upcoming occurrences partial for 30/60/90 days."""
    client.post(
        "/commitments",
        json={
            "description": "Weekly Groceries",
            "amount": "200.00",
            "due_date": "2026-08-25",
            "recurrence": "weekly",
            "category": "Food",
            "status": "pending",
        },
    )

    # 30 days
    res30 = client.get("/ui/upcoming?days=30")
    assert res30.status_code == 200
    assert "Weekly Groceries" in res30.text

    # 60 days
    res60 = client.get("/ui/upcoming?days=60")
    assert res60.status_code == 200
    assert "Weekly Groceries" in res60.text

    # 90 days
    res90 = client.get("/ui/upcoming?days=90")
    assert res90.status_code == 200
    assert "Weekly Groceries" in res90.text


def test_ui_commitment_form_modals(client: TestClient) -> None:
    """Test retrieving new and edit commitment modal forms."""
    # New form
    res_new = client.get("/ui/commitments/new")
    assert res_new.status_code == 200
    assert "Novo Compromisso" in res_new.text
    assert 'name="description"' in res_new.text

    # Create an item to edit
    create_res = client.post(
        "/commitments",
        json={
            "description": "Gym",
            "amount": "90.00",
            "due_date": "2026-09-01",
            "category": "Health",
        },
    )
    item_id = create_res.json()["id"]

    # Edit form
    res_edit = client.get(f"/ui/commitments/{item_id}/edit")
    assert res_edit.status_code == 200
    assert "Editar Compromisso" in res_edit.text
    assert "Gym" in res_edit.text


def test_ui_create_commitment_htmx(client: TestClient) -> None:
    """Test creating a commitment via HTMX form submission."""
    form_data = {
        "description": "Car Maintenance",
        "amount": "400.00",
        "due_date": "2026-09-15",
        "category": "Transport",
        "recurrence": "semiannual",
        "status": "pending",
        "is_estimate": "true",
    }
    res = client.post("/ui/commitments", data=form_data)
    assert res.status_code == 200
    assert "Car Maintenance" in res.text
    assert "cadastrado com sucesso" in res.text


def test_ui_update_commitment_htmx(client: TestClient) -> None:
    """Test updating a commitment via HTMX form submission."""
    create_res = client.post(
        "/commitments",
        json={
            "description": "Old Title",
            "amount": "100.00",
            "due_date": "2026-09-01",
            "category": "General",
        },
    )
    item_id = create_res.json()["id"]

    update_data = {
        "description": "Updated Title",
        "amount": "150.00",
        "due_date": "2026-09-05",
        "category": "General",
        "recurrence": "monthly",
        "status": "pending",
    }
    res = client.post(f"/ui/commitments/{item_id}/edit", data=update_data)
    assert res.status_code == 200
    assert "Updated Title" in res.text
    assert "atualizado com sucesso" in res.text


def test_ui_toggle_paid_and_delete_htmx(client: TestClient) -> None:
    """Test toggling paid status and deleting a commitment via HTMX."""
    create_res = client.post(
        "/commitments",
        json={
            "description": "Water Bill",
            "amount": "60.00",
            "due_date": "2026-09-01",
            "category": "Utilities",
            "status": "pending",
        },
    )
    item_id = create_res.json()["id"]

    # Toggle to paid
    toggle_res = client.post(f"/ui/commitments/{item_id}/toggle-paid")
    assert toggle_res.status_code == 200
    assert "marcado como pago" in toggle_res.text

    # Toggle back to pending
    toggle_back = client.post(f"/ui/commitments/{item_id}/toggle-paid")
    assert toggle_back.status_code == 200
    assert "reaberto como pendente" in toggle_back.text

    # Delete
    del_res = client.delete(f"/ui/commitments/{item_id}")
    assert del_res.status_code == 200
    assert "excluído com sucesso" in del_res.text


def test_ui_deposit_form_and_creation_htmx(client: TestClient) -> None:
    """Test deposit modal and deposit creation via HTMX."""
    modal_res = client.get("/ui/deposits/new")
    assert modal_res.status_code == 200
    assert "Registrar Depósito" in modal_res.text

    deposit_data = {
        "amount": "1000.00",
        "date": "2026-09-01",
        "note": "Emergency fund deposit",
    }
    create_res = client.post("/ui/deposits", data=deposit_data)
    assert create_res.status_code == 200
    assert (
        "Depósito de R$ 1,000.00 registrado com sucesso" in create_res.text
        or "1,000.00" in create_res.text
    )
