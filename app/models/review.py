"""Explicit occurrence confirmations; legacy records remain unclassified."""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OccurrenceReview(Base):
    __tablename__ = "occurrence_reviews"
    __table_args__ = (
        UniqueConstraint(
            "commitment_id", "occurrence_date", name="uq_occurrence_review"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    commitment_id: Mapped[int] = mapped_column(
        ForeignKey("commitments.id", ondelete="CASCADE"), nullable=False
    )
    occurrence_date: Mapped[date] = mapped_column(Date, nullable=False)
    nature: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unclassified"
    )
    date_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    reviewed_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
