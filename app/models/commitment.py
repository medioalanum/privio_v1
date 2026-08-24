"""Commitment database model and associated enums."""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecurrenceEnum(StrEnum):
    """Supported commitment recurrence frequencies."""

    NONE = "none"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"


class StatusEnum(StrEnum):
    """Supported commitment statuses."""

    PENDING = "pending"
    PAID = "paid"


class Commitment(Base):
    """SQLAlchemy model representing a financial commitment."""

    __tablename__ = "commitments"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    recurrence: Mapped[RecurrenceEnum] = mapped_column(
        SQLEnum(
            RecurrenceEnum,
            name="recurrence_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=RecurrenceEnum.NONE,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[StatusEnum] = mapped_column(
        SQLEnum(
            StatusEnum,
            name="status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=StatusEnum.PENDING,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
