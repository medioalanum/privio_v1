"""Financial, access, preservation and PDF layout regressions."""

from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import select

from app.database import Base
from app.models import Commitment, Payment
from app.models.commitment import RecurrenceEnum, StatusEnum
from app.services.monthly_report import monthly_data, render_monthly_pdf

MONTH = date(2026, 9, 1)
NOW = datetime(2026, 9, 9, 14, 35, tzinfo=UTC)


def bill(
    db,
    name="Energia",
    due=MONTH,
    amount="80",
    status=StatusEnum.PENDING,
    recurrence=RecurrenceEnum.NONE,
):
    item = Commitment(
        description=name,
        amount=Decimal(amount),
        due_date=due,
        category="Private category",
        recurrence=recurrence,
        status=status,
        is_estimate=False,
    )
    db.add(item)
    db.flush()
    return item


def snapshot(db):
    return {
        table.name: [
            tuple(row) for row in db.execute(select(table).order_by(table.c.id))
        ]
        for table in Base.metadata.sorted_tables
    }


def test_actual_paid_due_month_and_preservation(db_session):
    db = db_session
    paid = bill(db, "Aluguel", amount="100")
    db.add(
        Payment(
            commitment_id=paid.id,
            occurrence_date=MONTH,
            payment_date=date(2026, 8, 31),
            planned_amount=100,
            paid_amount=90,
        )
    )
    bill(db, "Internet", date(2026, 9, 15), "35")
    bill(db, "Anterior", date(2026, 8, 31), "999")
    bill(db, "Posterior", date(2026, 10, 1), "999")
    db.commit()
    before = snapshot(db)
    db.rollback()
    for _ in range(2):
        data = monthly_data(db, MONTH, NOW.date())
        assert data["known_paid"] == Decimal("90")
        assert data["due"] == Decimal("35")
        assert data["total"] == Decimal("125")
        pdf = render_monthly_pdf(data, MONTH, NOW, "pt")
        text = " ".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        assert "Aluguel" in text and "31/08/2026" in text
        assert "Anterior" not in text and "Posterior" not in text
        assert "Private category" not in text
        assert "09/09/2026 14:35:00 UTC" in text
        db.rollback()
    assert snapshot(db) == before


def test_legacy_future_payment_estimate_and_recurrence(db_session):
    db = db_session
    bill(db, "Legacy", status=StatusEnum.PAID)
    future = bill(db, "Future payment", amount="100")
    db.add(
        Payment(
            commitment_id=future.id,
            occurrence_date=MONTH,
            payment_date=date(2026, 9, 20),
            planned_amount=100,
            paid_amount=90,
        )
    )
    estimate = bill(
        db,
        "Estimate",
        amount="30",
        due=date(2026, 8, 15),
        recurrence=RecurrenceEnum.MONTHLY,
    )
    estimate.is_estimate = True
    db.commit()
    data = monthly_data(db, MONTH, NOW.date())
    assert data["incomplete"] and data["total"] is None
    assert data["due"] == Decimal("130")
    assert data["overdue"] == Decimal("100")
    assert len(data["rows"]) == 3
    assert any(r["nature"] == "estimated" for r in data["pending"])
    text = (
        PdfReader(BytesIO(render_monthly_pdf(data, MONTH, NOW, "pt")))
        .pages[0]
        .extract_text()
    )
    assert "Total incompleto" in text and "Não informado" in text and "Estimado" in text


@pytest.mark.parametrize("lang", ["pt", "en", "it"])
def test_empty_and_multi_page_pdf(db_session, lang):
    db = db_session
    empty = monthly_data(db, MONTH, NOW.date())
    assert empty["total"] == 0
    assert (
        len(PdfReader(BytesIO(render_monthly_pdf(empty, MONTH, NOW, lang))).pages) == 1
    )
    db.rollback()
    for i in range(75):
        bill(
            db,
            f"Conta {i:03d} - Água & manutenção <mensal> " + "descrição extensa " * 9,
        )
    db.commit()
    data = monthly_data(db, MONTH, NOW.date())
    pdf = PdfReader(BytesIO(render_monthly_pdf(data, MONTH, NOW, lang)))
    assert len(pdf.pages) > 2
    assert "Conta 000" in pdf.pages[0].extract_text()
    text = "\n".join(page.extract_text() for page in pdf.pages)
    for i in range(75):
        assert text.count(f"Conta {i:03d}") == 1
    for page in pdf.pages[1:]:
        assert "Vencimento" in page.extract_text() if lang == "pt" else True


@pytest.mark.parametrize("fixture", ["admin_client", "readonly_client"])
def test_download_both_roles(request, fixture):
    client = request.getfixturevalue(fixture)
    result = client.get("/reports/monthly.pdf?month=2026-09&lang=pt&q=ignored")
    assert result.status_code == 200
    assert result.headers["content-type"] == "application/pdf"
    assert result.headers["cache-control"] == "private, no-store"
    assert (
        'attachment; filename="Privio_2026-09_' in result.headers["content-disposition"]
    )
    assert result.content.startswith(b"%PDF-")
    home = client.get("/?month=2026-09&lang=pt")
    assert "/reports/monthly.pdf?month=2026-09&amp;lang=pt" in home.text


def test_anonymous_and_invalid_month(unauth_client, client):
    assert (
        unauth_client.get(
            "/reports/monthly.pdf?month=2026-09", follow_redirects=False
        ).status_code
        == 303
    )
    for month in ["2026-13", "2026-9", "0000-01", "9999-12", "garbage"]:
        assert client.get(f"/reports/monthly.pdf?month={month}").status_code == 422


def test_paid_only_and_empty_messages(db_session):
    db = db_session
    item = bill(db)
    db.add(
        Payment(
            commitment_id=item.id,
            occurrence_date=MONTH,
            payment_date=MONTH,
            planned_amount=80,
            paid_amount=75,
        )
    )
    db.commit()
    data = monthly_data(db, MONTH, NOW.date())
    assert data["due"] == 0 and data["total"] == Decimal("75")
    text = (
        PdfReader(BytesIO(render_monthly_pdf(data, MONTH, NOW, "pt")))
        .pages[0]
        .extract_text()
    )
    assert "Todas as contas deste mês estão marcadas como pagas." in text
