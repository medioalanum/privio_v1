"""Expected income is separate from received deposits."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExpectedIncome(Base):
    __tablename__ = "expected_income"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expected_date: Mapped[date] = mapped_column(Date, nullable=False)
    nature: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unclassified"
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("financial_accounts.id"), nullable=False
    )
    deposit_id: Mapped[int | None] = mapped_column(
        ForeignKey("deposits.id"), unique=True
    )
