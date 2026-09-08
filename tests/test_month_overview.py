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


def test_client_overview_has_no_operations(viewer_client, db_session):
    db_session.add(
        FinancialAccount(
            name="Synthetic", currency="EUR", opening_balance=100, account_type="bank"
        )
    )
    db_session.commit()
    page = viewer_client.get("/")
    assert page.status_code == 200
    assert 'id="coverage-title"' in page.text
    assert 'max="100"' in page.text
    assert "hx-post=" not in page.text
    assert "hx-delete=" not in page.text
    assert "/ui/commitments/new" not in page.text
    assert 'id="accounts-panel"' not in page.text
    assert 'href="/docs"' not in page.text


def test_admin_keeps_operations(editor_client):
    page = editor_client.get("/").text
    assert "/ui/commitments/new" in page
    assert 'id="accounts-panel"' in page
    assert 'id="coverage-title"' not in page


def test_forecast_carries_balance_and_arrears_once(db_session):
    from app.models import ExpectedIncome

    bank = FinancialAccount(
        name="Bank", currency="EUR", opening_balance=100, account_type="bank"
    )
    db_session.add(bank)
    db_session.flush()
    old = add_bill(db_session, "10", 1)
    old.due_date = date(2026, 8, 1)
    add_bill(db_session, "20", 9)
    later = add_bill(db_session, "40", 1)
    later.due_date = date(2026, 10, 1)
    db_session.add(
        ExpectedIncome(
            description="Future",
            amount=50,
            expected_date=date(2026, 10, 2),
            account_id=bank.id,
            nature="confirmed",
        )
    )
    db_session.commit()
    bills = list(db_session.scalars(select(Commitment)))
    result = decision_summary(db_session, bills, TODAY, TODAY)
    assert result["current"] == 100
    first, second = result["cash_months"][:2]
    assert first["pending"] == 30 and first["closing"] == 70
    assert second["opening"] == 70 and second["closing"] == 80
    assert second["pending"] == 40 and second["income"] == 50
    assert (
        decision_summary(db_session, bills, date(2025, 1, 1), TODAY)["cash_months"]
        == result["cash_months"]
    )


def test_both_dashboards_preserve_all_database_rows(
    editor_client, viewer_client, db_session
):
    from app.database import Base
    from scripts.migrate import migrate

    add_bill(db_session, "12.34", 5)
    db_session.commit()

    def snapshot():
        return {
            t.name: [tuple(row) for row in db_session.execute(select(t))]
            for t in Base.metadata.sorted_tables
        }

    before = snapshot()
    for client in [editor_client, viewer_client]:
        for month in ["2026-08", "2026-09", "2026-10"]:
            assert client.get("/", params={"month": month}).status_code == 200
    migrate(db_session.get_bind())
    migrate(db_session.get_bind())
    assert snapshot() == before
