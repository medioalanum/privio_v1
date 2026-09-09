"""Public demo isolation, synthetic data, permissions and reset regression tests."""

from datetime import date
from io import BytesIO
from unittest.mock import Mock

import pytest
from pypdf import PdfReader
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, settings
from app.models import Commitment, FinancialAccount, Payment
from scripts import demo


def test_demo_target_refused_before_connection(monkeypatch):
    target = Mock()
    monkeypatch.setattr(settings, "demo_mode", False)
    with pytest.raises(RuntimeError, match="DEMO_MODE"):
        demo.prepare(target, reset=True)
    target.begin.assert_not_called()
    monkeypatch.setattr(settings, "demo_mode", True)
    target.url.host = "company.example"
    target.url.database = "neondb"
    target.dialect.name = "postgresql"
    with pytest.raises(RuntimeError, match="pinned"):
        demo.prepare(target, reset=True)
    target.begin.assert_not_called()


def test_public_password_requires_demo():
    with pytest.raises(ValueError, match="demo mode"):
        Settings(
            _env_file=None,
            environment="production",
            admin_pass="test",
            client_pass="test",
            session_secret="independent-secret",
        )
    assert Settings(
        _env_file=None,
        environment="production",
        demo_mode=True,
        admin_pass="test",
        client_pass="test",
        session_secret="independent-secret",
    ).demo_mode


@pytest.mark.parametrize(
    "day", [date(2026, 9, 9), date(2026, 2, 1), date(2026, 12, 31)]
)
def test_synthetic_examples_and_pdf(admin_client, db_session, monkeypatch, day):
    monkeypatch.setattr(settings, "demo_mode", True)
    demo.populate(db_session, day)
    db_session.commit()
    assert db_session.scalar(select(func.count()).select_from(Payment)) == 2
    assert db_session.scalar(select(func.count()).select_from(FinancialAccount)) == 2
    assert all(
        "Demo" in bill.description for bill in db_session.scalars(select(Commitment))
    )
    for lang, notice in [
        ("pt", "Demonstração pública"),
        ("en", "Public demo"),
        ("it", "Demo pubblica"),
    ]:
        response = admin_client.get(f"/?lang={lang}&month={day:%Y-%m}")
        assert response.status_code == 200
        assert notice in response.text
        db_session.rollback()  # A real request receives a fresh database session.
        pdf = admin_client.get(f"/reports/monthly.pdf?month={day:%Y-%m}&lang={lang}")
        assert pdf.status_code == 200
        pages = PdfReader(BytesIO(pdf.content)).pages
        assert all("DEMO" in page.extract_text() for page in pages)


def test_demo_login_both_roles_and_client_denial(
    unauth_client, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "admin_pass", "test")
    monkeypatch.setattr(settings, "client_pass", "test")
    assert "senha test" in unauth_client.get("/login?lang=pt").text
    for role in ["admin", "client"]:
        response = unauth_client.post("/login", data={"role": role, "password": "test"})
        assert response.status_code == 200
        assert "demo-notice" in response.text
        if role == "client":
            assert unauth_client.post("/commitments", json={}).status_code == 403
        db_session.rollback()
        assert (
            unauth_client.get("/reports/monthly.pdf?month=2026-09").status_code == 200
        )
        unauth_client.post("/logout")


def test_demo_reset_atomic_and_restart_preserves_edits(db_session, monkeypatch):
    target = db_session.get_bind()
    if target.dialect.name != "postgresql":
        pytest.skip("PostgreSQL reset locking and rollback integration")
    # Only the disposable privio_test_ database selected by conftest is permitted.
    assert target.url.database.startswith("privio_test_")
    monkeypatch.setattr(demo, "check_target", lambda engine: None)
    demo.marker.drop(target, checkfirst=True)
    try:
        assert demo.prepare(target, today=date(2026, 9, 9))
        with Session(target) as db:
            bill = db.scalar(select(Commitment))
            assert bill is not None
            old_id = bill.id
            bill.description = "Visitor edit"
            db.commit()
        assert not demo.prepare(target)
        with Session(target) as db:
            edited = db.get(Commitment, old_id)
            assert edited is not None and edited.description == "Visitor edit"
        original_populate = demo.populate

        def fail(db, today):
            raise RuntimeError("simulated seed failure")

        monkeypatch.setattr(demo, "populate", fail)
        with pytest.raises(RuntimeError, match="simulated"):
            demo.prepare(target, reset=True)
        with Session(target) as db:
            edited = db.get(Commitment, old_id)
            assert edited is not None and edited.description == "Visitor edit"
        monkeypatch.setattr(demo, "populate", original_populate)
        assert demo.prepare(target, reset=True)
        with Session(target) as db:
            assert db.get(Commitment, old_id) is None
            assert db.scalar(select(func.count()).select_from(Commitment)) == 7
    finally:
        demo.marker.drop(target, checkfirst=True)


def test_unmarked_existing_database_is_preserved(db_session, monkeypatch):
    target = db_session.get_bind()
    if target.dialect.name != "postgresql":
        pytest.skip("PostgreSQL demo bootstrap integration")
    assert target.url.database.startswith("privio_test_")
    monkeypatch.setattr(demo, "check_target", lambda engine: None)
    demo.marker.drop(target, checkfirst=True)
    demo.populate(db_session, date(2026, 9, 9))
    db_session.commit()
    with pytest.raises(RuntimeError, match="existing records"):
        demo.prepare(target)
    assert db_session.scalar(select(func.count()).select_from(Commitment)) == 7
    db_session.rollback()
    demo.marker.drop(target, checkfirst=True)
