"""Reconcile pending obligations with cash without rewriting ledger records."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models import Commitment, FinancialAccount
from app.services.decisions import decision_summary
from tests.test_decisions import TODAY, add_bill


def test_arrears_are_included_once_and_next_date_is_grouped(db_session):
    old = add_bill(db_session, "80", 1)
    old.due_date = date(2026, 8, 1)
    add_bill(db_session, "20", 5)
    add_bill(db_session, "30", 9)
    add_bill(db_session, "40", 9)
    db_session.add(
        FinancialAccount(
            name="Bank", currency="EUR", opening_balance=100, account_type="bank"
        )
    )
    db_session.commit()
    bills = list(db_session.scalars(select(Commitment)))
    before = [(b.id, b.amount, b.due_date, b.status) for b in bills]
    result = decision_summary(db_session, bills, TODAY, TODAY)
    assert result["pending"] == 90
    assert result["due_total"] == 170
    assert result["difference"] == -70
    assert result["next_count"] == 2
    assert result["next_amount"] == 70
    assert len(result["operational_rows"]) == 4
    assert before == [(b.id, b.amount, b.due_date, b.status) for b in bills]


def test_coverage_empty_negative_unknown_and_future(db_session):
    account = FinancialAccount(
        name="Bank", currency="EUR", opening_balance=100, account_type="bank"
    )
    db_session.add(account)
    db_session.commit()
    assert decision_summary(db_session, [], TODAY, TODAY)["coverage"] == 100
    bill = add_bill(db_session, "20", 9)
    account.opening_balance = Decimal("-10")
    db_session.commit()
    summary = decision_summary(db_session, [bill], TODAY, TODAY)
    assert summary["coverage"] == 0
    assert summary["difference"] == -30
    assert (
        decision_summary(db_session, [bill], date(2026, 10, 1), TODAY)["difference"]
        is None
    )
    account.currency = "USD"
    db_session.commit()
    assert decision_summary(db_session, [bill], TODAY, TODAY)["coverage"] is None
