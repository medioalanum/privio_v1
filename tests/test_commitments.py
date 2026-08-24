"""Automated tests for Commitment CRUD, upcoming occurrences, and suggested monthly calculations."""

from decimal import Decimal

from fastapi.testclient import TestClient


def test_health_and_root(client: TestClient) -> None:
    """Test health check and root endpoints."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res = client.get("/")
    assert res.status_code == 200
    assert "Privio" in res.text
    assert "text/html" in res.headers["content-type"]


def test_create_commitment(client: TestClient) -> None:
    """Test creating a new commitment."""
    payload = {
        "description": "Internet Bill",
        "amount": "120.50",
        "is_estimate": False,
        "due_date": "2026-09-01",
        "recurrence": "monthly",
        "category": "Utilities",
        "status": "pending",
    }
    response = client.post("/commitments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["description"] == "Internet Bill"
    assert Decimal(data["amount"]) == Decimal("120.50")
    assert data["recurrence"] == "monthly"
    assert data["status"] == "pending"


def test_create_commitment_validation_error(client: TestClient) -> None:
    """Test validation errors on invalid input."""
    # Negative amount
    payload = {
        "description": "Invalid",
        "amount": "-50.00",
        "due_date": "2026-09-01",
        "category": "General",
    }
    response = client.post("/commitments", json=payload)
    assert response.status_code == 422

    # Invalid recurrence
    payload = {
        "description": "Invalid",
        "amount": "50.00",
        "due_date": "2026-09-01",
        "recurrence": "biweekly",  # not supported
        "category": "General",
    }
    response = client.post("/commitments", json=payload)
    assert response.status_code == 422


def test_get_commitment_by_id(client: TestClient) -> None:
    """Test fetching a single commitment."""
    create_res = client.post(
        "/commitments",
        json={
            "description": "Gym Membership",
            "amount": "80.00",
            "due_date": "2026-09-05",
            "category": "Health",
        },
    )
    item_id = create_res.json()["id"]

    res = client.get(f"/commitments/{item_id}")
    assert res.status_code == 200
    assert res.json()["description"] == "Gym Membership"

    # Not found test
    not_found = client.get("/commitments/99999")
    assert not_found.status_code == 404


def test_list_commitments_with_filters(client: TestClient) -> None:
    """Test listing and filtering commitments."""
    client.post(
        "/commitments",
        json={
            "description": "Rent",
            "amount": "1500.00",
            "due_date": "2026-09-01",
            "category": "Housing",
            "recurrence": "monthly",
            "status": "pending",
        },
    )
    client.post(
        "/commitments",
        json={
            "description": "Groceries",
            "amount": "300.00",
            "due_date": "2026-09-02",
            "category": "Food",
            "recurrence": "weekly",
            "status": "paid",
        },
    )

    # Filter by category
    res = client.get("/commitments?category=Housing")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["description"] == "Rent"

    # Filter by status
    res = client.get("/commitments?status=paid")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["description"] == "Groceries"

    # Filter by recurrence
    res = client.get("/commitments?recurrence=weekly")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_update_and_patch_commitment(client: TestClient) -> None:
    """Test PUT and PATCH updates."""
    create_res = client.post(
        "/commitments",
        json={
            "description": "Electricity",
            "amount": "100.00",
            "is_estimate": True,
            "due_date": "2026-09-10",
            "category": "Utilities",
            "status": "pending",
        },
    )
    item_id = create_res.json()["id"]

    # PUT (full update)
    put_payload = {
        "description": "Electricity Final",
        "amount": "115.50",
        "is_estimate": False,
        "due_date": "2026-09-12",
        "recurrence": "monthly",
        "category": "Utilities",
        "status": "paid",
    }
    put_res = client.put(f"/commitments/{item_id}", json=put_payload)
    assert put_res.status_code == 200
    assert put_res.json()["description"] == "Electricity Final"
    assert Decimal(put_res.json()["amount"]) == Decimal("115.50")
    assert put_res.json()["status"] == "paid"

    # PATCH (partial update)
    patch_res = client.patch(f"/commitments/{item_id}", json={"status": "pending"})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "pending"
    assert patch_res.json()["description"] == "Electricity Final"


def test_delete_commitment(client: TestClient) -> None:
    """Test deleting a commitment."""
    create_res = client.post(
        "/commitments",
        json={
            "description": "Old Subscription",
            "amount": "10.00",
            "due_date": "2026-09-01",
            "category": "Entertainment",
        },
    )
    item_id = create_res.json()["id"]

    del_res = client.delete(f"/commitments/{item_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/commitments/{item_id}")
    assert get_res.status_code == 404


def test_upcoming_occurrences_resolution(client: TestClient) -> None:
    """Test recurrence projection on GET /upcoming."""
    base_date = "2026-09-01"

    # 1. Non-recurring within range
    client.post(
        "/commitments",
        json={
            "description": "One-off Dentist",
            "amount": "200.00",
            "due_date": "2026-09-10",
            "recurrence": "none",
            "category": "Health",
        },
    )

    # 2. Weekly starting before window (2026-08-18)
    client.post(
        "/commitments",
        json={
            "description": "Weekly Piano Lesson",
            "amount": "50.00",
            "due_date": "2026-08-18",
            "recurrence": "weekly",
            "category": "Education",
        },
    )

    # 3. Monthly starting 2026-07-15
    client.post(
        "/commitments",
        json={
            "description": "Monthly Streaming",
            "amount": "15.00",
            "due_date": "2026-07-15",
            "recurrence": "monthly",
            "category": "Entertainment",
        },
    )

    # 4. Semiannual starting 2026-03-20 (next is 2026-09-20)
    client.post(
        "/commitments",
        json={
            "description": "Car Insurance Semiannual",
            "amount": "300.00",
            "due_date": "2026-03-20",
            "recurrence": "semiannual",
            "category": "Transport",
        },
    )

    # 5. Annual starting 2025-09-25 (next is 2026-09-25)
    client.post(
        "/commitments",
        json={
            "description": "Domain Renewal",
            "amount": "20.00",
            "due_date": "2025-09-25",
            "recurrence": "annual",
            "category": "Tech",
        },
    )

    # Query upcoming for 30 days starting 2026-09-01
    res = client.get(f"/upcoming?days=30&from_date={base_date}")
    assert res.status_code == 200
    occurrences = res.json()

    descriptions = [occ["description"] for occ in occurrences]

    # Weekly occurrences in September 2026 (from 2026-08-18):
    # 2026-08-18 + 14d = 2026-09-01
    # 2026-09-08
    # 2026-09-15
    # 2026-09-22
    # 2026-09-29
    piano_occurrences = [
        occ for occ in occurrences if occ["description"] == "Weekly Piano Lesson"
    ]
    assert len(piano_occurrences) == 5
    assert [occ["occurrence_date"] for occ in piano_occurrences] == [
        "2026-09-01",
        "2026-09-08",
        "2026-09-15",
        "2026-09-22",
        "2026-09-29",
    ]

    # Monthly occurrence (2026-09-15)
    assert "Monthly Streaming" in descriptions
    streaming_occ = next(
        occ for occ in occurrences if occ["description"] == "Monthly Streaming"
    )
    assert streaming_occ["occurrence_date"] == "2026-09-15"

    # Semiannual occurrence (2026-09-20)
    assert "Car Insurance Semiannual" in descriptions
    car_occ = next(
        occ for occ in occurrences if occ["description"] == "Car Insurance Semiannual"
    )
    assert car_occ["occurrence_date"] == "2026-09-20"

    # Annual occurrence (2026-09-25)
    assert "Domain Renewal" in descriptions
    domain_occ = next(
        occ for occ in occurrences if occ["description"] == "Domain Renewal"
    )
    assert domain_occ["occurrence_date"] == "2026-09-25"

    # One-off Dentist (2026-09-10)
    assert "One-off Dentist" in descriptions

    # Ensure results are sorted chronologically
    dates = [occ["occurrence_date"] for occ in occurrences]
    assert dates == sorted(dates)


def test_suggested_monthly_calculation(client: TestClient) -> None:
    """Test suggested monthly calculation: monthly + (annual / 12) + (semiannual / 6)."""
    # Monthly: 150.00
    client.post(
        "/commitments",
        json={
            "description": "Internet",
            "amount": "150.00",
            "due_date": "2026-09-01",
            "recurrence": "monthly",
            "category": "Utilities",
            "status": "pending",
        },
    )
    # Semiannual: 600.00 -> 600 / 6 = 100.00/mo
    client.post(
        "/commitments",
        json={
            "description": "Car Service",
            "amount": "600.00",
            "due_date": "2026-09-01",
            "recurrence": "semiannual",
            "category": "Transport",
            "status": "pending",
        },
    )
    # Annual: 1200.00 -> 1200 / 12 = 100.00/mo
    client.post(
        "/commitments",
        json={
            "description": "Property Tax",
            "amount": "1200.00",
            "due_date": "2026-09-01",
            "recurrence": "annual",
            "category": "Taxes",
            "status": "pending",
        },
    )
    # Paid commitment (should be excluded from active calculation)
    client.post(
        "/commitments",
        json={
            "description": "Paid Monthly Club",
            "amount": "500.00",
            "due_date": "2026-09-01",
            "recurrence": "monthly",
            "category": "Leisure",
            "status": "paid",
        },
    )

    res = client.get("/suggested-monthly")
    assert res.status_code == 200
    data = res.json()

    assert Decimal(data["monthly_sum"]) == Decimal("150.00")
    assert Decimal(data["semiannual_sum"]) == Decimal("600.00")
    assert Decimal(data["semiannual_contribution"]) == Decimal("100.00")
    assert Decimal(data["annual_sum"]) == Decimal("1200.00")
    assert Decimal(data["annual_contribution"]) == Decimal("100.00")
    assert Decimal(data["total_suggested_monthly"]) == Decimal("350.00")
    assert data["active_commitments_count"] == 3
