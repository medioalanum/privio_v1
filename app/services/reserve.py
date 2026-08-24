"""Reserve balance service calculation."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.commitment import Commitment, StatusEnum
from app.models.deposit import Deposit
from app.schemas.deposit import ReserveBalanceResponse
from app.services.recurrence import _quantize_currency


def calculate_reserve_balance(db: Session) -> ReserveBalanceResponse:
    """Calculate total deposits, total paid commitments, and net reserve balance.

    Formula: sum(deposits) - sum(commitments where status == 'paid')

    Args:
        db: Active SQLAlchemy database session.

    Returns:
        ReserveBalanceResponse containing deposit sum, paid commitment sum, and net balance.
    """
    deposit_sum = db.scalar(
        select(func.coalesce(func.sum(Deposit.amount), Decimal("0.00")))
    )
    total_deposits = _quantize_currency(Decimal(str(deposit_sum or "0.00")))

    paid_sum = db.scalar(
        select(func.coalesce(func.sum(Commitment.amount), Decimal("0.00"))).where(
            Commitment.status == StatusEnum.PAID
        )
    )
    total_paid = _quantize_currency(Decimal(str(paid_sum or "0.00")))

    reserve_balance = _quantize_currency(total_deposits - total_paid)

    deposits_count = db.scalar(select(func.count()).select_from(Deposit)) or 0
    paid_commitments_count = (
        db.scalar(
            select(func.count())
            .select_from(Commitment)
            .where(Commitment.status == StatusEnum.PAID)
        )
        or 0
    )

    return ReserveBalanceResponse(
        total_deposits=total_deposits,
        total_paid_commitments=total_paid,
        reserve_balance=reserve_balance,
        deposits_count=deposits_count,
        paid_commitments_count=paid_commitments_count,
    )
