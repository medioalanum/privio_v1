"""FastAPI main application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app import models as _models  # noqa: F401 - register tables before create_all
from app.config import settings
from app.database import Base, engine
from app.models.commitment import Commitment, CommitmentAdjustment, StatusEnum
from app.models.financial_account import FinancialAccount
from app.models.payment import Payment
from app.routers.commitments import router as commitments_router
from app.routers.deposits import router as deposits_router
from app.routers.web import router as web_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    # Attempt to create tables on startup if database is reachable
    try:
        Base.metadata.create_all(bind=engine)
        columns = {
            column["name"]
            for column in inspect(engine).get_columns("commitment_adjustments")
        }
        if "adjusted_date" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE commitment_adjustments "
                        "ADD COLUMN adjusted_date DATE"
                    )
                )
        inspector = inspect(engine)
        for table_name in ("deposits", "payments"):
            table_columns = {
                column["name"] for column in inspector.get_columns(table_name)
            }
            if "account_id" not in table_columns:
                with engine.begin() as connection:
                    connection.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN account_id INTEGER")
                    )

        with Session(engine) as session:
            default_account = session.scalar(
                select(FinancialAccount).where(
                    FinancialAccount.name == "Recursos a distribuir"
                )
            )
            if default_account is None:
                default_account = FinancialAccount(
                    name="Recursos a distribuir",
                    account_type="allocation",
                    responsible="Principal",
                    currency="EUR",
                    opening_balance=0,
                    notes="Valores recebidos que ainda não foram distribuídos.",
                )
                session.add(default_account)
                session.flush()

            paid_adjustments = session.scalars(
                select(CommitmentAdjustment).where(
                    CommitmentAdjustment.scope == "single",
                    CommitmentAdjustment.status == StatusEnum.PAID,
                    CommitmentAdjustment.is_deleted.is_(False),
                )
            ).all()
            for adjustment in paid_adjustments:
                occurrence_date = adjustment.adjusted_date or adjustment.effective_date
                exists = session.scalar(
                    select(Payment).where(
                        Payment.commitment_id == adjustment.commitment_id,
                        Payment.occurrence_date == occurrence_date,
                    )
                )
                if exists is None:
                    commitment = session.get(Commitment, adjustment.commitment_id)
                    if commitment is not None:
                        amount = adjustment.amount or commitment.amount
                        session.add(
                            Payment(
                                commitment_id=commitment.id,
                                occurrence_date=occurrence_date,
                                payment_date=occurrence_date,
                                planned_amount=amount,
                                paid_amount=amount,
                                account_id=default_account.id,
                                note="Migrated from previous paid status",
                            )
                        )
            session.commit()
    except Exception:
        # Fallback if DB is not immediately available or when running unit test suites
        pass
    yield


app = FastAPI(
    title=settings.app_name,
    description="FastAPI Commitment & Recurrence Financial Management API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(commitments_router)
app.include_router(deposits_router)
app.include_router(web_router)


@app.get("/health", tags=["System"], summary="Health check")
def health_check() -> dict[str, str]:
    """Health check endpoint to verify service availability."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/", tags=["System"], summary="Root endpoint")
def root() -> dict[str, str]:
    """Root endpoint welcoming API consumers and linking to docs."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs_url": "/docs",
        "health_url": "/health",
    }
