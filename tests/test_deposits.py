"""Automated tests for Deposit CRUD and /reserve-balance calculation."""

from decimal import Decimal

from fastapi.testclient import TestClient


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
