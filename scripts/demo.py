"""Initialize or reset only the explicitly allowlisted public demonstration database."""

import argparse
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    Table,
    delete,
    func,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine
from app.models import (
    Commitment,
    Deposit,
    ExpectedIncome,
    FinancialAccount,
    Payment,
    RecurrenceEnum,
)

# Public endpoint identity, not a credential. Never add the company's endpoint here.
DEMO_HOST = "ep-ancient-night-b1otlakh-pooler.c-5.eu-central-1.aws.neon.tech"
marker = Table(
    "privio_demo_state",
    MetaData(),
    Column("id", Integer, primary_key=True),
    Column("reset_at", DateTime(timezone=True), nullable=False),
)


def check_target(target: Engine) -> None:
    if not settings.demo_mode:
        raise RuntimeError("Demo operations require DEMO_MODE=true")
    url = target.url
    if (url.host, url.database) != (
        DEMO_HOST,
        "neondb",
    ) or target.dialect.name != "postgresql":
        raise RuntimeError("Refusing database outside the pinned demo endpoint")


def populate(db: Session, today: date) -> None:
    """Synthetic EUR examples with dates that remain useful as months change."""
    month = today.replace(day=1)
    bank = FinancialAccount(
        name="Banco Horizonte — Demo",
        opening_balance=Decimal("2400"),
        currency="EUR",
        responsible="Equipe Demo",
    )
    reserve = FinancialAccount(
        name="Reserva — Demo",
        account_type="cash",
        opening_balance=Decimal("850"),
        currency="EUR",
    )
    db.add_all([bank, reserve])
    db.flush()
    income = Deposit(
        amount=Decimal("1850"),
        date=month,
        note="Receita de serviços — exemplo",
        account_id=bank.id,
    )
    db.add(income)
    db.flush()
    db.add_all(
        [
            ExpectedIncome(
                description="Serviços recebidos — Demo",
                amount=Decimal("1850"),
                expected_date=month,
                account_id=bank.id,
                deposit_id=income.id,
                nature="confirmed",
            ),
            ExpectedIncome(
                description="Próximo recebimento — Demo",
                amount=Decimal("1200"),
                expected_date=today + timedelta(days=7),
                account_id=bank.id,
                nature="estimated",
            ),
        ]
    )
    for description, amount, due, category, paid, estimate in [
        ("Aluguel do escritório", "780", month, "Estrutura", True, False),
        ("Internet", "49.90", month, "Serviços", True, False),
        (
            "Material de escritório",
            "125",
            today - timedelta(days=3),
            "Operação",
            False,
            False,
        ),
        ("Energia elétrica", "145", today, "Serviços", False, True),
        (
            "Software de gestão",
            "39",
            today + timedelta(days=3),
            "Tecnologia",
            False,
            False,
        ),
        (
            "Contabilidade",
            "210",
            month + relativedelta(day=28),
            "Serviços",
            False,
            False,
        ),
        (
            "Seguro empresarial",
            "90",
            month + relativedelta(months=1, day=10),
            "Estrutura",
            False,
            False,
        ),
    ]:
        bill = Commitment(
            description=description + " — Demo",
            amount=Decimal(amount),
            due_date=due,
            category=category,
            recurrence=RecurrenceEnum.MONTHLY,
            is_estimate=estimate,
        )
        db.add(bill)
        db.flush()
        if paid:
            db.add(
                Payment(
                    commitment_id=bill.id,
                    occurrence_date=due,
                    payment_date=due,
                    planned_amount=bill.amount,
                    paid_amount=bill.amount,
                    account_id=bank.id,
                    note="Pagamento fictício",
                )
            )


def prepare(target: Engine, *, reset: bool = False, today: date | None = None) -> bool:
    check_target(target)  # Must happen before any connection or DDL.
    with target.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(7386202610)"))
        marker.create(connection, checkfirst=True)
        # Serialize against browser writes. Preserve sequences so stale forms cannot
        # accidentally address a replacement example with the same primary key.
        tables = list(Base.metadata.sorted_tables)
        names = ", ".join('"' + table.name + '"' for table in tables)
        connection.execute(
            text(f"LOCK TABLE {names}, privio_demo_state IN ACCESS EXCLUSIVE MODE")
        )
        initialized = connection.execute(select(marker.c.id)).first() is not None
        if initialized and not reset:
            return False
        if not initialized and any(
            connection.scalar(select(func.count()).select_from(table))
            for table in tables
        ):
            raise RuntimeError(
                "Refusing to initialize an unmarked database with existing records"
            )
        if reset and not initialized:
            raise RuntimeError("Reset requires a previously initialized demo marker")
        for table in reversed(tables):
            connection.execute(delete(table))
        with Session(bind=connection) as db:
            populate(db, today or datetime.now(UTC).date())
            db.flush()
        connection.execute(delete(marker))
        connection.execute(marker.insert().values(id=1, reset_at=datetime.now(UTC)))
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Replace the initialized demo examples atomically",
    )
    args = parser.parse_args()
    changed = prepare(engine, reset=args.reset)
    print(
        "Demo examples refreshed."
        if changed
        else "Demo already initialized; records preserved."
    )
