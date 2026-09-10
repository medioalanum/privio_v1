"""Financial read paths must not mutate records or invent reconciled balances."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.database import Base
from app.models.commitment import Commitment
from app.models.deposit import Deposit
from app.models.financial_account import AccountTransfer, FinancialAccount
from app.models.payment import Payment
from app.services.decisions import decision_summary
from app.services.ledger import ledger_rows


def seed(db):
    bank = FinancialAccount(
        name="Synthetic bank", account_type="bank", opening_balance=0
    )
    allocation = FinancialAccount(
        name="Unreconciled", account_type="allocation", opening_balance=0
    )
    db.add_all([bank, allocation])
    db.flush()
    db.add(
        Deposit(
            amount=2400,
            date=date(2026, 8, 24),
            account_id=bank.id,
            note="Synthetic income",
        )
    )
    for description, amount, day in [
        ("Synthetic rent", 1200, 24),
        ("Synthetic school", 440, 24),
        ("Synthetic service", 500, 25),
        ("Synthetic fee", 3, 25),
    ]:
        bill = Commitment(
            description=description,
            amount=amount,
            due_date=date(2026, 8, day),
            category="Test",
        )
        db.add(bill)
        db.flush()
        db.add(
            Payment(
                commitment_id=bill.id,
                occurrence_date=bill.due_date,
                payment_date=bill.due_date,
                planned_amount=amount,
                paid_amount=amount,
                account_id=bank.id,
            )
        )
    db.commit()
    return bank, allocation


def snapshot(db):
    return {
        table.name: list(db.execute(select(table).order_by(table.c.id)))
        for table in Base.metadata.sorted_tables
    }


@pytest.mark.parametrize("lang", ["pt", "en", "it"])
def test_navigation_ledger_and_full_record_preservation(
    admin_client, readonly_client, db_session, lang
):
    bank, _ = seed(db_session)
    before = snapshot(db_session)
    for client in (admin_client, readonly_client):
        for view in ("month", "accounts", "recurring"):
            for status in ("pending", "paid", "all"):
                page = client.get(
                    f"/?month=2026-08&lang={lang}&view={view}&status={status}"
                )
                assert page.status_code == 200
        accounts = client.get(
            f"/?view=accounts&month=2026-08&lang={lang}&ledger_account={bank.id}"
        ).text
        assert "Synthetic bank" in accounts and (
            "257,00" in accounts or "257.00" in accounts
        )
        assert "deposit-" in accounts and "payment-" in accounts
    paid = admin_client.get("/?month=2026-08&status=paid").text
    assert "€ 440,00" in paid and "status=pending#upcoming-section" in paid
    pending = admin_client.get("/?month=2026-08&status=pending").text
    assert "Synthetic rent" not in pending
    assert snapshot(db_session) == before


def test_unknown_assignment_blocks_consolidated_projection(db_session):
    bank, allocation = seed(db_session)
    bills = list(db_session.scalars(select(Commitment)))
    assert decision_summary(db_session, bills, date(2026, 9, 1), date(2026, 9, 10))[
        "current"
    ] == Decimal("257")
    dep = Deposit(amount=10, date=date(2026, 8, 26), account_id=None)
    db_session.add(dep)
    db_session.commit()
    assert (
        decision_summary(db_session, bills, date(2026, 9, 1), date(2026, 9, 10))[
            "current"
        ]
        is None
    )
    dep.account_id = allocation.id
    db_session.commit()
    assert (
        decision_summary(db_session, bills, date(2026, 9, 1), date(2026, 9, 10))[
            "current"
        ]
        is None
    )
    history = ledger_rows(db_session, date(2026, 8, 1), date(2026, 9, 10), str(bank.id))
    assert history[-1]["balance"] == Decimal("257")


def test_ledger_transfer_dates_currency_and_future_exclusion(db_session):
    bank, _ = seed(db_session)
    other = FinancialAccount(
        name="Other", account_type="bank", opening_balance=5, currency="USD"
    )
    db_session.add(other)
    db_session.flush()
    db_session.add_all(
        [
            AccountTransfer(
                from_account_id=bank.id,
                to_account_id=other.id,
                amount=10,
                date=date(2026, 9, 1),
            ),
            Deposit(amount=999, date=date(2026, 10, 1), account_id=bank.id),
        ]
    )
    db_session.commit()
    before = snapshot(db_session)
    rows = ledger_rows(db_session, date(2026, 9, 1), date(2026, 9, 10), None)
    assert len(rows) == 2 and sum(r["amount"] for r in rows) == 0
    assert {r["balance"] for r in rows} == {Decimal("247"), Decimal("15")}
    assert ledger_rows(db_session, date(2026, 10, 1), date(2026, 9, 10), None) == []
    assert snapshot(db_session) == before


def test_paid_history_uses_due_month_but_ledger_uses_payment_date(
    admin_client, db_session
):
    bank, _ = seed(db_session)
    bill = Commitment(
        description="August paid in September",
        amount=40,
        due_date=date(2026, 8, 28),
        category="Test",
    )
    db_session.add(bill)
    db_session.flush()
    db_session.add(
        Payment(
            commitment_id=bill.id,
            occurrence_date=bill.due_date,
            payment_date=date(2026, 9, 1),
            planned_amount=40,
            paid_amount=35,
            account_id=bank.id,
        )
    )
    db_session.commit()
    page = admin_client.get("/?month=2026-08&status=paid").text
    assert "August paid in September" in page and "€ 35,00" in page
    aug = ledger_rows(db_session, date(2026, 8, 1), date(2026, 9, 10), str(bank.id))
    sept = ledger_rows(db_session, date(2026, 9, 1), date(2026, 9, 10), str(bank.id))
    assert all(r["description"] != "August paid in September" for r in aug)
    assert sept[0]["amount"] == Decimal("-35")


def test_account_create_returns_account_page_and_client_cannot_write(
    admin_client, readonly_client
):
    payload = {
        "name": "New synthetic account",
        "account_type": "bank",
        "opening_balance": "0",
    }
    assert (
        readonly_client.post("/ui/accounts?view=accounts", data=payload).status_code
        == 403
    )
    response = admin_client.post(
        "/ui/accounts?view=accounts&month=2026-08", data=payload
    )
    assert response.status_code == 200 and 'id="ledger"' in response.text
    assert (
        admin_client.post("/ui/accounts?view=accounts", data=payload).status_code == 409
    )
    form = admin_client.get("/ui/deposits/new").text
    assert "disabled selected" in form and 'hx-sync="this:drop"' in form
