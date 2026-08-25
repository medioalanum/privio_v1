"""Reserve balance and monthly cash-flow calculations."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.commitment import Commitment, StatusEnum
from app.models.deposit import Deposit
from app.models.financial_account import AccountTransfer, FinancialAccount
from app.models.payment import Payment
from app.schemas.deposit import (
    AccountBalanceResponse,
    FinancialPositionResponse,
    MonthlyCashFlowResponse,
    MonthlyForecastResponse,
    ReserveBalanceResponse,
)
from app.services.recurrence import _quantize_currency, resolve_upcoming_occurrences


def calculate_monthly_cash_flow(
    db: Session,
    commitments: Sequence[Commitment],
    month: date,
) -> MonthlyCashFlowResponse:
    """Calculate actual scheduled, paid, and available amounts for one month."""
    month_start = month.replace(day=1)
    month_end = month_start + relativedelta(months=1, days=-1)
    occurrences = resolve_upcoming_occurrences(
        commitments,
        from_date=month_start,
        days=(month_end - month_start).days,
    )
    payments = db.scalars(
        select(Payment).where(
            Payment.occurrence_date >= month_start,
            Payment.occurrence_date <= month_end,
        )
    ).all()
    payment_by_occurrence = {
        (payment.commitment_id, payment.occurrence_date): payment
        for payment in payments
    }

    deposit_values = db.scalars(
        select(Deposit.amount).where(
            Deposit.date >= month_start,
            Deposit.date <= month_end,
        )
    ).all()
    received = _quantize_currency(sum(deposit_values, start=Decimal("0.00")))
    bills_total = _quantize_currency(
        sum((item.amount for item in occurrences), start=Decimal("0.00"))
    )
    paid_occurrences = [
        item
        for item in occurrences
        if item.status == StatusEnum.PAID
        or (item.original_commitment_id, item.occurrence_date) in payment_by_occurrence
    ]
    paid = _quantize_currency(
        sum(
            (
                payment_by_occurrence[
                    (item.original_commitment_id, item.occurrence_date)
                ].paid_amount
                if (item.original_commitment_id, item.occurrence_date)
                in payment_by_occurrence
                else item.amount
                for item in paid_occurrences
            ),
            start=Decimal("0.00"),
        )
    )
    pending = _quantize_currency(
        sum(
            (item.amount for item in occurrences if item not in paid_occurrences),
            start=Decimal("0.00"),
        )
    )
    available_now = _quantize_currency(received - paid)
    projected_balance = _quantize_currency(available_now - pending)

    return MonthlyCashFlowResponse(
        month=month_start,
        received=received,
        bills_total=bills_total,
        paid=paid,
        pending=pending,
        available_now=available_now,
        projected_balance=projected_balance,
        deposits_count=len(deposit_values),
        bills_count=len(occurrences),
        paid_count=len(paid_occurrences),
        pending_count=len(occurrences) - len(paid_occurrences),
    )


def calculate_cash_flow_forecast(
    db: Session,
    commitments: Sequence[Commitment],
    start_month: date,
    months: int = 12,
) -> list[MonthlyForecastResponse]:
    """Return exact calendar-month requirements without annualized averages."""
    rows: list[MonthlyForecastResponse] = []
    for offset in range(months):
        month = start_month.replace(day=1) + relativedelta(months=offset)
        flow = calculate_monthly_cash_flow(db, commitments, month)
        month_end = month + relativedelta(months=1, days=-1)
        occurrences = resolve_upcoming_occurrences(
            commitments, month, (month_end - month).days
        )
        notable = [
            item.description
            for item in occurrences
            if item.recurrence.value in {"semiannual", "annual"}
        ]
        status = (
            "paid"
            if flow.bills_count > 0 and flow.pending_count == 0
            else "partial"
            if flow.paid_count > 0
            else "pending"
        )
        rows.append(
            MonthlyForecastResponse(
                month=month,
                total=flow.bills_total,
                paid=flow.paid,
                pending=flow.pending,
                status=status,
                notable_items=notable,
            )
        )
    return rows


def calculate_financial_position(
    db: Session,
    commitments: Sequence[Commitment],
    start_month: date,
) -> FinancialPositionResponse:
    """Calculate where money is held and what remains free after 12 months."""
    accounts = db.scalars(
        select(FinancialAccount)
        .where(FinancialAccount.is_active.is_(True))
        .order_by(FinancialAccount.id)
    ).all()
    default_account = next(
        (account for account in accounts if account.account_type == "allocation"), None
    )
    deposits = db.scalars(select(Deposit)).all()
    payments = db.scalars(select(Payment)).all()
    transfers = db.scalars(select(AccountTransfer)).all()

    balances: dict[int, Decimal] = {
        account.id: Decimal(account.opening_balance) for account in accounts
    }
    for deposit in deposits:
        account_id = deposit.account_id or (
            default_account.id if default_account is not None else None
        )
        if account_id in balances:
            balances[account_id] += Decimal(deposit.amount)
    for payment in payments:
        account_id = payment.account_id or (
            default_account.id if default_account is not None else None
        )
        if account_id in balances:
            balances[account_id] -= Decimal(payment.paid_amount)
    for transfer in transfers:
        if transfer.from_account_id in balances:
            balances[transfer.from_account_id] -= Decimal(transfer.amount)
        if transfer.to_account_id in balances:
            balances[transfer.to_account_id] += Decimal(transfer.amount)

    account_rows = [
        AccountBalanceResponse(
            id=account.id,
            name=account.name,
            account_type=account.account_type,
            responsible=account.responsible,
            currency=account.currency,
            balance=_quantize_currency(balances[account.id]),
            notes=account.notes,
        )
        for account in accounts
    ]
    total_resources = _quantize_currency(
        sum((row.balance for row in account_rows), start=Decimal("0.00"))
    )
    forecast = calculate_cash_flow_forecast(db, commitments, start_month, months=12)
    obligations = _quantize_currency(
        sum((row.pending for row in forecast), start=Decimal("0.00"))
    )
    return FinancialPositionResponse(
        total_resources=total_resources,
        obligations=obligations,
        free_to_spend=_quantize_currency(total_resources - obligations),
        accounts=account_rows,
    )


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
