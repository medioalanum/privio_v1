"""Business logic for recurrence resolution and financial suggestions."""

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from dateutil.relativedelta import relativedelta

from app.models.commitment import Commitment, RecurrenceEnum, StatusEnum
from app.schemas.commitment import (
    CommitmentOccurrenceResponse,
    SuggestedMonthlyResponse,
)


def _quantize_currency(value: Decimal) -> Decimal:
    """Helper to round monetary amounts to 2 decimal places."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def resolve_upcoming_occurrences(
    commitments: Sequence[Commitment],
    from_date: date,
    days: int,
) -> list[CommitmentOccurrenceResponse]:
    """Calculate all commitment occurrences falling within the [from_date, from_date + days] window.

    For recurring commitments, future occurrences are projected from the original due_date.

    Args:
        commitments: Collection of commitments to evaluate.
        from_date: Start date of the upcoming window.
        days: Number of days in the future to project.

    Returns:
        List of CommitmentOccurrenceResponse items sorted chronologically by occurrence date.
    """
    to_date = from_date + timedelta(days=days)
    occurrences: list[CommitmentOccurrenceResponse] = []

    for item in commitments:
        # Non-recurring: only include if due_date falls in the window and status is pending
        if item.recurrence == RecurrenceEnum.NONE:
            if from_date <= item.due_date <= to_date:
                occurrences.append(
                    CommitmentOccurrenceResponse(
                        original_commitment_id=item.id,
                        description=item.description,
                        amount=item.amount,
                        is_estimate=item.is_estimate,
                        original_due_date=item.due_date,
                        occurrence_date=item.due_date,
                        days_until=(item.due_date - from_date).days,
                        recurrence=item.recurrence,
                        category=item.category,
                        status=item.status,
                    )
                )
            continue

        # If recurring start date is after our window end, it has no occurrences in this window
        if item.due_date > to_date:
            continue

        # Weekly recurrence
        if item.recurrence == RecurrenceEnum.WEEKLY:
            if item.due_date < from_date:
                days_diff = (from_date - item.due_date).days
                steps = days_diff // 7
                cur_date = item.due_date + timedelta(days=steps * 7)
                while cur_date < from_date:
                    cur_date += timedelta(days=7)
            else:
                cur_date = item.due_date

            while cur_date <= to_date:
                occurrences.append(
                    CommitmentOccurrenceResponse(
                        original_commitment_id=item.id,
                        description=item.description,
                        amount=item.amount,
                        is_estimate=item.is_estimate,
                        original_due_date=item.due_date,
                        occurrence_date=cur_date,
                        days_until=(cur_date - from_date).days,
                        recurrence=item.recurrence,
                        category=item.category,
                        status=item.status,
                    )
                )
                cur_date += timedelta(days=7)

        # Monthly recurrence
        elif item.recurrence == RecurrenceEnum.MONTHLY:
            approx_months = (
                (from_date.year - item.due_date.year) * 12
                + (from_date.month - item.due_date.month)
                - 1
            )
            k = max(0, approx_months)

            while item.due_date + relativedelta(months=k) < from_date:
                k += 1

            while True:
                occ_date = item.due_date + relativedelta(months=k)
                if occ_date > to_date:
                    break
                if occ_date >= from_date:
                    occurrences.append(
                        CommitmentOccurrenceResponse(
                            original_commitment_id=item.id,
                            description=item.description,
                            amount=item.amount,
                            is_estimate=item.is_estimate,
                            original_due_date=item.due_date,
                            occurrence_date=occ_date,
                            days_until=(occ_date - from_date).days,
                            recurrence=item.recurrence,
                            category=item.category,
                            status=item.status,
                        )
                    )
                k += 1

        # Semiannual recurrence (every 6 months)
        elif item.recurrence == RecurrenceEnum.SEMIANNUAL:
            approx_k = max(
                0,
                (
                    (from_date.year - item.due_date.year) * 12
                    + (from_date.month - item.due_date.month)
                )
                // 6
                - 1,
            )
            k = approx_k

            while item.due_date + relativedelta(months=6 * k) < from_date:
                k += 1

            while True:
                occ_date = item.due_date + relativedelta(months=6 * k)
                if occ_date > to_date:
                    break
                if occ_date >= from_date:
                    occurrences.append(
                        CommitmentOccurrenceResponse(
                            original_commitment_id=item.id,
                            description=item.description,
                            amount=item.amount,
                            is_estimate=item.is_estimate,
                            original_due_date=item.due_date,
                            occurrence_date=occ_date,
                            days_until=(occ_date - from_date).days,
                            recurrence=item.recurrence,
                            category=item.category,
                            status=item.status,
                        )
                    )
                k += 1

        # Annual recurrence (every 1 year)
        elif item.recurrence == RecurrenceEnum.ANNUAL:
            approx_k = max(0, from_date.year - item.due_date.year - 1)
            k = approx_k

            while item.due_date + relativedelta(years=k) < from_date:
                k += 1

            while True:
                occ_date = item.due_date + relativedelta(years=k)
                if occ_date > to_date:
                    break
                if occ_date >= from_date:
                    occurrences.append(
                        CommitmentOccurrenceResponse(
                            original_commitment_id=item.id,
                            description=item.description,
                            amount=item.amount,
                            is_estimate=item.is_estimate,
                            original_due_date=item.due_date,
                            occurrence_date=occ_date,
                            days_until=(occ_date - from_date).days,
                            recurrence=item.recurrence,
                            category=item.category,
                            status=item.status,
                        )
                    )
                k += 1

    # Sort all occurrences by occurrence_date, then by description
    occurrences.sort(key=lambda o: (o.occurrence_date, o.original_commitment_id))
    return occurrences


def calculate_suggested_monthly(
    commitments: Sequence[Commitment],
    only_active: bool = True,
) -> SuggestedMonthlyResponse:
    """Calculate the suggested monthly budget based on active commitments.

    Formula: monthly + (annual / 12) + (semiannual / 6)

    Args:
        commitments: Collection of commitments to evaluate.
        only_active: Whether to restrict calculation to status == PENDING.

    Returns:
        SuggestedMonthlyResponse containing total and itemized breakdown.
    """
    monthly_sum = Decimal("0.00")
    semiannual_sum = Decimal("0.00")
    annual_sum = Decimal("0.00")
    active_count = 0

    for item in commitments:
        if only_active and item.status != StatusEnum.PENDING:
            continue

        active_count += 1
        if item.recurrence == RecurrenceEnum.MONTHLY:
            monthly_sum += item.amount
        elif item.recurrence == RecurrenceEnum.SEMIANNUAL:
            semiannual_sum += item.amount
        elif item.recurrence == RecurrenceEnum.ANNUAL:
            annual_sum += item.amount

    semiannual_contribution = _quantize_currency(semiannual_sum / Decimal(6))
    annual_contribution = _quantize_currency(annual_sum / Decimal(12))
    monthly_sum = _quantize_currency(monthly_sum)
    semiannual_sum = _quantize_currency(semiannual_sum)
    annual_sum = _quantize_currency(annual_sum)

    total_suggested_monthly = _quantize_currency(
        monthly_sum + semiannual_contribution + annual_contribution
    )

    return SuggestedMonthlyResponse(
        total_suggested_monthly=total_suggested_monthly,
        monthly_sum=monthly_sum,
        semiannual_sum=semiannual_sum,
        semiannual_contribution=semiannual_contribution,
        annual_sum=annual_sum,
        annual_contribution=annual_contribution,
        active_commitments_count=active_count,
    )
