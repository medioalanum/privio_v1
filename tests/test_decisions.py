"""Synthetic regression and cash-flow boundary tests, independent of wall clock."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models import Commitment, Deposit, FinancialAccount, OccurrenceReview, Payment
from app.models.commitment import RecurrenceEnum, StatusEnum
from app.services.decisions import decision_summary
from scripts.migrate import migrate

TODAY = date(2026, 9, 7)


def add_bill(db, amount, day, estimate=False):
    bill = Commitment(
        description=f"Synthetic {day} {amount}",
        amount=Decimal(amount),
        due_date=date(2026, 9, day),
        category="Test",
        recurrence=RecurrenceEnum.NONE,
        status=StatusEnum.PENDING,
        is_estimate=estimate,
    )
    db.add(bill)
    db.flush()
    return bill


def test_historical_fixture(db_session):
    db = db_session
    # Twenty synthetic occurrences; no real descriptions or customer identifiers.
    add_bill(db, "362.50", 5)
    for amount in ["338.11", "503.16", "71.50"]:
        add_bill(db, amount, 9)
    for day in [12, 19, 26]:
        add_bill(db, "362.50", day)
    add_bill(db, "400.00", 15)
    for amount in ["5000", "300", "500", "300", "160"]:
        add_bill(db, amount, 20, True)
    for amount in ["1200", "130", "500", "100", "600", "200", "120"]:
        add_bill(db, amount, 20)
    db.commit()
    summary = decision_summary(db, list(db.scalars(select(Commitment))), TODAY, TODAY)
    assert len(summary["rows"]) == 20
    assert summary["total"] == Decimal("11872.77")
    assert summary["overdue"] == Decimal("362.50")
    assert summary["next_seven"] == Decimal("1275.27")
    assert summary["estimated"] == Decimal("6260.00")
    assert sum(
        (r["pending"] for r in summary["rows"] if r["item"].occurrence_date.day == 20),
        Decimal(0),
    ) == Decimal("9110")
    assert summary["current"] is None
    assert summary["projected"] is None


def test_payment_month_and_no_double_count(db_session):
    db = db_session
    account = FinancialAccount(
        name="Synthetic bank",
        opening_balance=Decimal("1000"),
        currency="EUR",
        account_type="bank",
    )
    db.add(account)
    db.flush()
    bill = add_bill(db, "100", 5)
    db.add(
        Payment(
            commitment_id=bill.id,
            occurrence_date=bill.due_date,
            payment_date=date(2026, 8, 31),
            planned_amount=100,
            paid_amount=90,
            account_id=account.id,
        )
    )
    db.add(Deposit(amount=200, date=TODAY, account_id=account.id))
    add_bill(db, "50", 7)
    db.commit()
    summary = decision_summary(db, list(db.scalars(select(Commitment))), TODAY, TODAY)
    assert summary["current"] == Decimal("1110")
    assert summary["projected"] == Decimal("1060")
    assert summary["realized"] == Decimal("200")
    assert summary["settled_planned"] == Decimal("100")
    assert summary["pending"] == Decimal("50")
    assert summary["total"] == summary["settled_planned"] + summary["pending"]


def test_seven_days_and_explicit_review(db_session):
    db = db_session
    bills = [add_bill(db, "10", day) for day in (6, 7, 13, 14)]
    db.add(
        OccurrenceReview(
            commitment_id=bills[1].id,
            occurrence_date=bills[1].due_date,
            nature="confirmed",
            reviewed_amount=Decimal("10"),
            date_confirmed=True,
        )
    )
    db.commit()
    summary = decision_summary(db, bills, TODAY, TODAY)
    assert summary["overdue"] == 10
    assert summary["next_seven"] == 20
    assert summary["rows"][1]["nature"] == "confirmed"
    assert summary["rows"][0]["nature"] == "unclassified"
    assert summary["rows"][1]["date_confirmed"]
    assert not summary["rows"][0]["date_confirmed"]


def test_additive_migration_is_repeatable(db_session):
    db = db_session
    bill = add_bill(db, "12.34", 5)
    db.commit()
    before = (bill.id, bill.description, bill.amount, bill.due_date, bill.status)
    migrate(db.get_bind())
    migrate(db.get_bind())
    db.expire_all()
    after = db.get(Commitment, bill.id)
    assert before == (
        after.id,
        after.description,
        after.amount,
        after.due_date,
        after.status,
    )
    assert list(db.scalars(select(Payment))) == []


def test_mixed_currency_and_past_month_unknown(db_session):
    db = db_session
    db.add_all(
        [
            FinancialAccount(name="USD", currency="USD", opening_balance=10),
            FinancialAccount(name="EUR", currency="EUR", opening_balance=10),
        ]
    )
    db.commit()
    summary = decision_summary(db, [], date(2026, 8, 1), TODAY)
    assert summary["current"] is None
    assert summary["projected"] is None
    assert summary["past"]


def test_expected_income_receipt_not_double_counted(client, db_session):
    from app.models import ExpectedIncome

    account = FinancialAccount(name="Income test", currency="EUR", opening_balance=100)
    db_session.add(account)
    db_session.flush()
    income = ExpectedIncome(
        description="Synthetic receipt",
        amount=50,
        expected_date=date.today(),
        nature="confirmed",
        account_id=account.id,
    )
    db_session.add(income)
    db_session.commit()
    before = decision_summary(db_session, [], date.today(), date.today())
    assert before["current"] == 100
    assert before["projected"] == 150
    for _ in range(2):
        response = client.post(
            f"/ui/income/{income.id}/receive",
            data={"received_date": str(date.today()), "received_amount": "50.00"},
        )
        assert response.status_code == 200
    after = decision_summary(db_session, [], date.today(), date.today())
    assert after["current"] == 150
    assert after["projected"] == 150
    assert len(list(db_session.scalars(select(Deposit)))) == 1


def test_payment_duplicate_and_invalid_amount(client, db_session):
    bill = add_bill(db_session, "20", 5)
    db_session.commit()
    payload = {
        "commitment_id": bill.id,
        "occurrence_date": str(bill.due_date),
        "payment_date": "2026-09-05",
        "planned_amount": "999",
        "paid_amount": "20",
    }
    for _ in range(2):
        assert client.post("/ui/payments", data=payload).status_code == 200
    payments = list(db_session.scalars(select(Payment)))
    assert len(payments) == 1
    assert payments[0].planned_amount == 20
    assert (
        client.post("/ui/payments", data={**payload, "paid_amount": "21"}).status_code
        == 409
    )
    assert (
        client.post("/ui/payments", data={**payload, "paid_amount": "-1"}).status_code
        == 422
    )


def test_viewer_cannot_confirm_or_receive(viewer_client):
    assert (
        viewer_client.post(
            "/ui/reviews",
            data={
                "commitment_id": 1,
                "occurrence_date": "2026-09-05",
                "nature": "confirmed",
            },
        ).status_code
        == 403
    )
    assert (
        viewer_client.post(
            "/ui/income/1/receive",
            data={"received_date": "2026-09-05", "received_amount": "1"},
        ).status_code
        == 403
    )


def test_recurrence_boundaries_and_far_moved_date(db_session):
    from app.models.commitment import CommitmentAdjustment
    from app.services.recurrence import resolve_upcoming_occurrences

    bill = Commitment(
        description="Month end",
        amount=Decimal("10.01"),
        due_date=date(2024, 1, 31),
        category="Test",
        recurrence=RecurrenceEnum.MONTHLY,
        status=StatusEnum.PENDING,
        is_estimate=False,
    )
    db_session.add(bill)
    db_session.flush()
    rows = resolve_upcoming_occurrences([bill], date(2024, 2, 1), 59)
    assert [r.occurrence_date for r in rows] == [date(2024, 2, 29), date(2024, 3, 31)]
    adjustment = CommitmentAdjustment(
        commitment_id=bill.id,
        effective_date=date(2024, 1, 31),
        adjusted_date=date(2024, 9, 10),
        scope="single",
        is_deleted=False,
    )
    db_session.add(adjustment)
    db_session.commit()
    db_session.refresh(bill)
    moved = resolve_upcoming_occurrences([bill], date(2024, 9, 10), 0)
    assert len(moved) == 1
    assert moved[0].amount == Decimal("10.01")


def test_rounding_negative_balance_and_internal_transfer(db_session):
    from app.models import AccountTransfer
    from app.services.recurrence import _quantize_currency

    assert _quantize_currency(Decimal("2.345")) == Decimal("2.35")
    a = FinancialAccount(name="A", currency="EUR", opening_balance=10)
    b = FinancialAccount(name="B", currency="EUR", opening_balance=20)
    db_session.add_all([a, b])
    db_session.flush()
    db_session.add(
        AccountTransfer(from_account_id=a.id, to_account_id=b.id, amount=5, date=TODAY)
    )
    bill = add_bill(db_session, "40", 9)
    db_session.commit()
    flow = decision_summary(db_session, [bill], TODAY, TODAY)
    assert flow["current"] == 30
    assert flow["projected"] == -10
    assert flow["first_negative"] == date(2026, 9, 9)


def test_concurrent_payment_submission_postgres(db_session):
    from concurrent.futures import ThreadPoolExecutor

    import pytest
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session

    from app.config import settings
    from app.database import get_db
    from app.main import app
    from tests.conftest import _get_basic_auth_header

    if db_session.get_bind().dialect.name != "postgresql":
        pytest.skip("Requires independent PostgreSQL transactions")
    bill = add_bill(db_session, "25", 5)
    db_session.commit()
    payload = {
        "commitment_id": bill.id,
        "occurrence_date": str(bill.due_date),
        "payment_date": "2026-09-05",
        "planned_amount": "25",
        "paid_amount": "25",
    }
    engine = db_session.get_bind()

    def sessions():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = sessions
    try:
        with TestClient(
            app,
            headers=_get_basic_auth_header(settings.editor_user, settings.editor_pass),
        ) as client:
            with ThreadPoolExecutor(max_workers=2) as pool:
                codes = list(
                    pool.map(
                        lambda _: client.post("/ui/payments", data=payload).status_code,
                        range(2),
                    )
                )
        assert codes == [200, 200]
        assert len(list(db_session.scalars(select(Payment)))) == 1
    finally:
        app.dependency_overrides.clear()
