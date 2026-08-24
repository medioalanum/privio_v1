"""Automated tests for Deposit CRUD and /reserve-balance calculation."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.commitment import Commitment
from app.services.reserve import (
    calculate_cash_flow_forecast,
    calculate_monthly_cash_flow,
)


def test_create_deposit(client: TestClient) -> None:
    """Test creating a new deposit record."""
    payload = {
        "amount": "1500.00",
        "date": "2026-09-01",
        "note": "Monthly salary transfer",
    }
    response = client.post("/deposits", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert Decimal(data["amount"]) == Decimal("1500.00")
    assert data["date"] == "2026-09-01"
    assert data["note"] == "Monthly salary transfer"


def test_create_deposit_validation_error(client: TestClient) -> None:
    """Test validation errors for invalid deposit payload."""
    # Negative amount
    payload = {
        "amount": "-100.00",
        "date": "2026-09-01",
    }
    response = client.post("/deposits", json=payload)
    assert response.status_code == 422


def test_get_deposit_by_id(client: TestClient) -> None:
    """Test retrieving a single deposit by ID."""
    create_res = client.post(
        "/deposits",
        json={
            "amount": "250.00",
            "date": "2026-09-02",
            "note": "Bonus transfer",
        },
    )
    deposit_id = create_res.json()["id"]

    res = client.get(f"/deposits/{deposit_id}")
    assert res.status_code == 200
    assert Decimal(res.json()["amount"]) == Decimal("250.00")

    # 404 test
    not_found = client.get("/deposits/99999")
    assert not_found.status_code == 404


def test_list_deposits_with_filters(client: TestClient) -> None:
    """Test listing deposits with date filters."""
    client.post(
        "/deposits", json={"amount": "100.00", "date": "2026-09-01", "note": "D1"}
    )
    client.post(
        "/deposits", json={"amount": "200.00", "date": "2026-09-10", "note": "D2"}
    )
    client.post(
        "/deposits", json={"amount": "300.00", "date": "2026-09-20", "note": "D3"}
    )

    # Filter start_date
    res1 = client.get("/deposits?start_date=2026-09-10")
    assert res1.status_code == 200
    assert len(res1.json()) == 2

    # Filter end_date
    res2 = client.get("/deposits?end_date=2026-09-10")
    assert res2.status_code == 200
    assert len(res2.json()) == 2


def test_update_and_patch_deposit(client: TestClient) -> None:
    """Test PUT and PATCH operations on deposits."""
    create_res = client.post(
        "/deposits",
        json={"amount": "500.00", "date": "2026-09-01", "note": "Initial"},
    )
    deposit_id = create_res.json()["id"]

    # PUT
    put_res = client.put(
        f"/deposits/{deposit_id}",
        json={"amount": "600.00", "date": "2026-09-02", "note": "Updated"},
    )
    assert put_res.status_code == 200
    assert Decimal(put_res.json()["amount"]) == Decimal("600.00")
    assert put_res.json()["note"] == "Updated"

    # PATCH
    patch_res = client.patch(
        f"/deposits/{deposit_id}",
        json={"amount": "750.00"},
    )
    assert patch_res.status_code == 200
    assert Decimal(patch_res.json()["amount"]) == Decimal("750.00")
    assert patch_res.json()["note"] == "Updated"


def test_delete_deposit(client: TestClient) -> None:
    """Test deleting a deposit."""
    create_res = client.post(
        "/deposits",
        json={"amount": "50.00", "date": "2026-09-01"},
    )
    deposit_id = create_res.json()["id"]

    del_res = client.delete(f"/deposits/{deposit_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/deposits/{deposit_id}")
    assert get_res.status_code == 404


def test_reserve_balance_calculation(client: TestClient) -> None:
    """Test GET /reserve-balance: total_deposits - total_paid_commitments."""
    # 1. Initially empty
    empty_res = client.get("/reserve-balance")
    assert empty_res.status_code == 200
    empty_data = empty_res.json()
    assert Decimal(empty_data["total_deposits"]) == Decimal("0.00")
    assert Decimal(empty_data["total_paid_commitments"]) == Decimal("0.00")
    assert Decimal(empty_data["reserve_balance"]) == Decimal("0.00")
    assert empty_data["deposits_count"] == 0
    assert empty_data["paid_commitments_count"] == 0

    # 2. Add deposits: 1000.00 + 500.00 = 1500.00
    client.post(
        "/deposits",
        json={"amount": "1000.00", "date": "2026-09-01", "note": "Transfer 1"},
    )
    client.post(
        "/deposits",
        json={"amount": "500.00", "date": "2026-09-02", "note": "Transfer 2"},
    )

    # 3. Add commitments
    # Paid commitment 1: 300.00
    client.post(
        "/commitments",
        json={
            "description": "Paid Electric Bill",
            "amount": "300.00",
            "due_date": "2026-09-01",
            "category": "Utilities",
            "status": "paid",
        },
    )
    # Paid commitment 2: 200.00
    client.post(
        "/commitments",
        json={
            "description": "Paid Water Bill",
            "amount": "200.00",
            "due_date": "2026-09-02",
            "category": "Utilities",
            "status": "paid",
        },
    )
    # Pending commitment (should NOT be deducted from reserve balance): 450.00
    client.post(
        "/commitments",
        json={
            "description": "Pending Rent",
            "amount": "450.00",
            "due_date": "2026-09-05",
            "category": "Housing",
            "status": "pending",
        },
    )

    # 4. Check /reserve-balance
    # Total deposits: 1500.00
    # Total paid commitments: 500.00
    # Reserve balance: 1500.00 - 500.00 = 1000.00
    res = client.get("/reserve-balance")
    assert res.status_code == 200
    data = res.json()
    assert Decimal(data["total_deposits"]) == Decimal("1500.00")
    assert Decimal(data["total_paid_commitments"]) == Decimal("500.00")
    assert Decimal(data["reserve_balance"]) == Decimal("1000.00")
    assert data["deposits_count"] == 2
    assert data["paid_commitments_count"] == 2


def test_monthly_cash_flow_uses_actual_occurrences(
    client: TestClient, db_session: Session
) -> None:
    """Cash flow must use actual monthly due dates, overrides, and deposits."""
    client.post("/deposits", json={"amount": "2400.00", "date": "2026-08-03"})
    client.post("/deposits", json={"amount": "999.00", "date": "2026-09-01"})

    monthly = client.post(
        "/commitments",
        json={
            "description": "Monthly school",
            "amount": "400.00",
            "due_date": "2026-08-15",
            "recurrence": "monthly",
            "category": "Education",
        },
    ).json()
    client.post(
        f"/ui/commitments/{monthly['id']}/edit",
        data={
            "description": "Monthly school",
            "amount": "440.00",
            "due_date": "2026-08-24",
            "category": "Education",
            "recurrence": "monthly",
            "status": "pending",
            "scope": "single",
            "occurrence_date": "2026-08-15",
        },
    )
    client.post(
        f"/ui/commitments/{monthly['id']}/toggle-paid",
        params={"occurrence_date": "2026-08-24"},
    )

    for description, amount, due_date, recurrence in (
        ("Weekly", "100.00", "2026-08-01", "weekly"),
        ("Semiannual", "600.00", "2026-08-10", "semiannual"),
        ("Annual", "1200.00", "2026-08-20", "annual"),
    ):
        client.post(
            "/commitments",
            json={
                "description": description,
                "amount": amount,
                "due_date": due_date,
                "recurrence": recurrence,
                "category": "Test",
            },
        )

    removed = client.post(
        "/commitments",
        json={
            "description": "Removed one-off",
            "amount": "50.00",
            "due_date": "2026-08-12",
            "category": "Test",
        },
    ).json()
    client.delete(f"/ui/commitments/{removed['id']}/occurrences/2026-08-12")

    commitments = db_session.scalars(select(Commitment)).all()
    flow = calculate_monthly_cash_flow(db_session, commitments, date(2026, 8, 1))

    assert flow.received == Decimal("2400.00")
    assert flow.bills_total == Decimal("2740.00")
    assert flow.paid == Decimal("440.00")
    assert flow.pending == Decimal("2300.00")
    assert flow.available_now == Decimal("1960.00")
    assert flow.projected_balance == Decimal("-340.00")
    assert flow.deposits_count == 1
    assert flow.bills_count == 8
    assert flow.paid_count == 1
    assert flow.pending_count == 7


def test_twelve_month_forecast_uses_full_due_amounts(
    client: TestClient, db_session: Session
) -> None:
    """Annual and semiannual amounts belong in their actual due month."""
    for description, amount, due_date, recurrence in (
        ("Monthly", "100.00", "2026-08-05", "monthly"),
        ("Annual tax", "1200.00", "2026-10-10", "annual"),
        ("Semiannual insurance", "600.00", "2026-11-10", "semiannual"),
    ):
        client.post(
            "/commitments",
            json={
                "description": description,
                "amount": amount,
                "due_date": due_date,
                "recurrence": recurrence,
                "category": "Test",
            },
        )
    commitments = db_session.scalars(select(Commitment)).all()
    rows = calculate_cash_flow_forecast(
        db_session, commitments, date(2026, 8, 1), months=4
    )
    assert [row.total for row in rows] == [
        Decimal("100.00"),
        Decimal("100.00"),
        Decimal("1300.00"),
        Decimal("700.00"),
    ]
    assert rows[2].notable_items == ["Annual tax"]
    assert rows[3].notable_items == ["Semiannual insurance"]
