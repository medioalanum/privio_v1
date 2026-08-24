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
    assert "Recebido no Mês" in response.text
    assert "Saldo Projetado" in response.text
    assert "Internet Fiber" in response.text
    assert (
        "R$ 120.00" in response.text
        or "R$ 120,00" in response.text
        or "120.00" in response.text
    )


def test_month_navigation_filters_and_survives_actions(client: TestClient) -> None:
    """The selected month controls the dashboard and survives HTMX actions."""
    client.post(
        "/commitments",
        json={
            "description": "August only",
            "amount": "80.00",
            "due_date": "2026-08-10",
            "category": "Test",
        },
    )
    september = client.post(
        "/commitments",
        json={
            "description": "September only",
            "amount": "90.00",
            "due_date": "2026-09-10",
            "category": "Test",
        },
    ).json()

    page = client.get("/?month=2026-09&lang=pt")
    assert page.status_code == 200
    assert "Setembro 2026" in page.text
    assert "September only" in page.text
    assert (
        "August only"
        not in page.text.split('id="upcoming-section"', 1)[1].split("</section>", 1)[0]
    )
    assert "month=2026-08" in page.text
    assert "month=2026-10" in page.text

    edited = client.post(
        f"/ui/commitments/{september['id']}/edit?month=2026-09",
        data={
            "description": "September changed",
            "amount": "95.00",
            "due_date": "2026-09-10",
            "category": "Test",
            "recurrence": "none",
            "status": "pending",
            "scope": "series",
        },
    )
    assert edited.status_code == 200
    assert "Setembro 2026" in edited.text
    assert "September changed" in edited.text


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


def test_recurring_occurrence_edit_scopes_and_single_delete(
    client: TestClient,
) -> None:
    """Single and future edits must not overwrite the complete recurring series."""
    created = client.post(
        "/commitments",
        json={
            "description": "School Pedro",
            "amount": "400.00",
            "due_date": "2026-08-15",
            "recurrence": "monthly",
            "category": "Education",
            "status": "pending",
        },
    )
    commitment_id = created.json()["id"]
    base_form = {
        "description": "School Pedro",
        "due_date": "2026-09-15",
        "category": "Education",
        "recurrence": "monthly",
        "status": "pending",
    }

    single = client.post(
        f"/ui/commitments/{commitment_id}/edit",
        data={
            **base_form,
            "due_date": "2026-08-24",
            "amount": "440.00",
            "scope": "single",
            "occurrence_date": "2026-08-15",
        },
    )
    assert single.status_code == 200
    assert "ocorrência de 15/08/2026 atualizada" in single.text
    assert "440.00" in single.text
    assert "24/08/2026" in single.text
    assert 'aria-label="Excluir somente esta ocorrência"' in single.text

    paid = client.post(
        f"/ui/commitments/{commitment_id}/toggle-paid",
        params={"occurrence_date": "2026-08-24"},
    )
    assert paid.status_code == 200
    assert "marcado como pago" in paid.text
    assert "School Pedro" in paid.text
    assert "Pago" in paid.text
    assert 'aria-label="↩ Reabrir"' in paid.text
    assert client.get(f"/commitments/{commitment_id}").json()["status"] == "pending"

    reopened = client.post(
        f"/ui/commitments/{commitment_id}/toggle-paid",
        params={"occurrence_date": "2026-08-24"},
    )
    assert reopened.status_code == 200
    assert "reaberto como pendente" in reopened.text
    assert "Pendente" in reopened.text
    assert 'aria-label="✓ Marcar Pago"' in reopened.text

    suggested = client.get("/suggested-monthly").json()
    assert suggested["monthly_sum"] == "440.00"

    future = client.post(
        f"/ui/commitments/{commitment_id}/edit",
        data={
            **base_form,
            "amount": "450.00",
            "scope": "future",
            "occurrence_date": "2026-10-15",
        },
    )
    assert future.status_code == 200

    occurrences = client.get("/upcoming?from_date=2026-08-01&days=130").json()
    amounts = {
        item["occurrence_date"]: item["amount"]
        for item in occurrences
        if item["description"] == "School Pedro"
    }
    assert "2026-08-15" not in amounts
    assert amounts["2026-08-24"] == "440.00"
    assert amounts["2026-09-15"] == "400.00"
    assert amounts["2026-10-15"] == "450.00"
    assert amounts["2026-11-15"] == "450.00"

    deleted = client.delete(f"/ui/commitments/{commitment_id}/occurrences/2026-11-15")
    assert deleted.status_code == 200
    after_delete = client.get("/upcoming?from_date=2026-09-01&days=100").json()
    dates = {
        item["occurrence_date"]
        for item in after_delete
        if item["description"] == "School Pedro"
    }
    assert "2026-11-15" not in dates

    base = client.get(f"/commitments/{commitment_id}").json()
    assert base["amount"] == "400.00"

    series = client.post(
        f"/ui/commitments/{commitment_id}/edit",
        data={
            **base_form,
            "description": "School Pedro updated",
            "amount": "475.00",
            "due_date": "2026-08-20",
            "scope": "series",
            "occurrence_date": "2026-08-15",
        },
    )
    assert series.status_code == 200
    updated_base = client.get(f"/commitments/{commitment_id}").json()
    assert updated_base["description"] == "School Pedro updated"
    assert updated_base["amount"] == "475.00"
    assert updated_base["due_date"] == "2026-08-20"

    removed_series = client.delete(f"/ui/commitments/{commitment_id}")
    assert removed_series.status_code == 200
    assert client.get(f"/commitments/{commitment_id}").status_code == 404
