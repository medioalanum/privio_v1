"""Commitment database model and associated enums."""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    adjustments: Mapped[list["CommitmentAdjustment"]] = relationship(
        back_populates="commitment", cascade="all, delete-orphan", lazy="selectin"
    )


class CommitmentAdjustment(Base):
    """An override for one occurrence or for all occurrences from a date onward."""

    __tablename__ = "commitment_adjustments"
    __table_args__ = (
        UniqueConstraint(
            "commitment_id", "effective_date", "scope", name="uq_commitment_adjustment"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    commitment_id: Mapped[int] = mapped_column(
        ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    adjusted_date: Mapped[date | None] = mapped_column(Date)
    scope: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    is_estimate: Mapped[bool | None] = mapped_column(Boolean)
    category: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[StatusEnum | None] = mapped_column(
        SQLEnum(
            StatusEnum,
            name="adjustment_status_enum",
            values_callable=lambda x: [e.value for e in x],
        )
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    commitment: Mapped[Commitment] = relationship(back_populates="adjustments")
