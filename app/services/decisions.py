"""Read-only decision model. Unknown inputs stay unknown; money uses Decimal."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal
from typing import TypedDict

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.commitment import Commitment, StatusEnum
from app.models.deposit import Deposit
from app.models.financial_account import AccountTransfer, FinancialAccount
from app.models.income import ExpectedIncome
from app.models.payment import Payment
from app.models.review import OccurrenceReview
from app.schemas.commitment import CommitmentOccurrenceResponse
from app.services.recurrence import resolve_upcoming_occurrences


class DecisionRow(TypedDict):
    item: CommitmentOccurrenceResponse
    payment: Payment | None
    pending: Decimal
    nature: str
    status: str
    date_confirmed: bool


class TimelineRow(TypedDict):
    date: date
    inflow: Decimal
    outflow: Decimal
    balance: Decimal | None


ZERO = Decimal("0.00")


def decision_summary(
    db: Session, commitments: Sequence[Commitment], month: date, today: date
) -> dict:
    """Current ledger through today; projection through selected month end.

    Seven days means today through today+6 inclusive. Overdue includes all prior
    dates and is placed at today in projections without changing its due date.
    Existing Payment records settle an occurrence (including negotiated amounts);
    the old application does not implement cumulative partial payments.
    """
    start = month.replace(day=1)
    end = start + relativedelta(months=1, days=-1)
    accounts = list(
        db.scalars(select(FinancialAccount).where(FinancialAccount.is_active.is_(True)))
    )
    deposits = list(db.scalars(select(Deposit)))
    payments = list(db.scalars(select(Payment)))
    transfers = list(db.scalars(select(AccountTransfer)))
    paid = {(p.commitment_id, p.occurrence_date): p for p in payments}
    first = min([c.due_date for c in commitments] + [start, today])
    horizon = max(
        start + relativedelta(months=12, days=-1), today + relativedelta(months=6)
    )
    occurrences = resolve_upcoming_occurrences(
        commitments, first, (horizon - first).days
    )
    reviews = {
        (r.commitment_id, r.occurrence_date): r
        for r in db.scalars(select(OccurrenceReview))
    }
    rows: list[DecisionRow] = []
    legacy_paid = False
    for occurrence in occurrences:
        payment = paid.get(
            (occurrence.original_commitment_id, occurrence.occurrence_date)
        )
        if payment is not None:
            occurrence.amount = payment.planned_amount
        settled = payment is not None and payment.payment_date <= today
        legacy = occurrence.status == StatusEnum.PAID and payment is None
        legacy_paid |= legacy
        pending = ZERO if settled or legacy else occurrence.amount
        nature = (
            "estimated"
            if occurrence.is_estimate or "ESTIMATIVA" in occurrence.description.upper()
            else "unclassified"
        )
        review = reviews.get(
            (occurrence.original_commitment_id, occurrence.occurrence_date)
        )
        if review and review.reviewed_amount == occurrence.amount:
            nature = review.nature
        rows.append(
            {
                "item": occurrence,
                "payment": payment,
                "pending": pending,
                "nature": nature,
                "date_confirmed": bool(review and review.date_confirmed),
                "status": "paid"
                if settled or legacy
                else "overdue"
                if occurrence.occurrence_date < today
                else "pending",
            }
        )
    month_rows = [r for r in rows if start <= r["item"].occurrence_date <= end]
    balances = {a.id: Decimal(a.opening_balance) for a in accounts}
    default = next((a.id for a in accounts if a.account_type == "allocation"), None)
    incomplete = (
        not accounts
        or legacy_paid
        or all(a.account_type == "allocation" for a in accounts)
    )
    for movement, sign, date_field in [
        (deposits, 1, "date"),
        (payments, -1, "payment_date"),
    ]:
        for entry in movement:
            if getattr(entry, date_field) > today:
                continue
            account = entry.account_id or default
            if entry.account_id is None:
                incomplete = True
            if (
                account in balances
                and next(a for a in accounts if a.id == account).account_type
                == "allocation"
            ):
                incomplete = True
            if account not in balances:
                incomplete = True
            else:
                balances[account] += sign * Decimal(
                    entry.amount if isinstance(entry, Deposit) else entry.paid_amount
                )
    for transfer in transfers:
        if transfer.date <= today:
            if transfer.from_account_id in balances:
                balances[transfer.from_account_id] -= transfer.amount
            if transfer.to_account_id in balances:
                balances[transfer.to_account_id] += transfer.amount
    # Commitments have no currency field: only the established EUR scope is safe.
    currencies = {a.currency for a in accounts}
    incomplete |= currencies != {"EUR"}
    incomplete |= any(
        a.account_type == "allocation" and balances[a.id] != ZERO for a in accounts
    )
    current = None if incomplete else sum(balances.values(), ZERO)
    daily = defaultdict(lambda: {"inflow": ZERO, "outflow": ZERO})
    if end >= today:
        for row in rows:
            due = row["item"].occurrence_date
            if due <= end and row["pending"]:
                daily[max(today, due)]["outflow"] += row["pending"]
    incomes = list(
        db.scalars(select(ExpectedIncome).where(ExpectedIncome.deposit_id.is_(None)))
    )
    included_income = []
    for income in incomes:
        if today <= income.expected_date <= end and income.account_id in {
            a.id for a in accounts if a.currency == "EUR"
        }:
            daily[income.expected_date]["inflow"] += income.amount
            included_income.append(income)
    running = current
    timeline: list[TimelineRow] = []
    first_negative = today if current is not None and current < 0 else None
    for day, values in sorted(daily.items()):
        if running is not None:
            running += values["inflow"] - values["outflow"]
            if running < 0 and first_negative is None:
                first_negative = day
        timeline.append(
            {
                "date": day,
                "inflow": values["inflow"],
                "outflow": values["outflow"],
                "balance": running,
            }
        )
    received = sum(
        (d.amount for d in deposits if start <= d.date <= min(end, today)), ZERO
    )
    realized_paid = sum(
        (p.paid_amount for p in payments if start <= p.payment_date <= min(end, today)),
        ZERO,
    )
    month_pending = sum((r["pending"] for r in month_rows), ZERO)
    total = sum((r["item"].amount for r in month_rows), ZERO)
    next_due = next(
        (r for r in rows if r["pending"] and r["item"].occurrence_date >= today), None
    )
    concentration = max(timeline, key=lambda r: r["outflow"], default=None)
    graph_dates = [today] + [r["date"] for r in timeline]
    graph_values = [
        v for v in [current] + [r["balance"] for r in timeline] if v is not None
    ]
    graph = ""
    if current is not None and len(graph_values) > 1:
        low, high = min(graph_values), max(graph_values)
        span = high - low or Decimal(1)
        graph = " ".join(
            f"{10 + (graph_dates[i] - today).days * 580 / max(1, (end - today).days):.1f},{190 - float((v - low) / span) * 170:.1f}"
            for i, v in enumerate(graph_values)
        )
    forecast = []
    for offset in range(12):
        forecast_month = start + relativedelta(months=offset)
        next_month = forecast_month + relativedelta(months=1)
        scheduled = [
            r for r in rows if forecast_month <= r["item"].occurrence_date < next_month
        ]
        total_scheduled = sum((r["item"].amount for r in scheduled), ZERO)
        pending_scheduled = sum((r["pending"] for r in scheduled), ZERO)
        forecast.append(
            {
                "month": forecast_month,
                "total": total_scheduled,
                "paid": total_scheduled - pending_scheduled,
                "pending": pending_scheduled,
                "status": "paid"
                if scheduled and not pending_scheduled
                else "partial"
                if pending_scheduled < total_scheduled
                else "pending",
                "notable_items": [
                    r["item"].description
                    for r in scheduled
                    if r["item"].recurrence.value in {"annual", "semiannual"}
                ],
            }
        )
    # The operational month includes older pending bills once, never paid history.
    operational = sorted(
        [r for r in rows if r["item"].occurrence_date <= end and r["pending"]]
        if start <= today <= end
        else month_rows,
        key=lambda r: (r["item"].occurrence_date, r["item"].original_commitment_id),
    )
    due_total = sum((r["pending"] for r in operational), ZERO)
    difference = (
        current - due_total if current is not None and start <= today <= end else None
    )
    future_pending = [
        r for r in rows if r["pending"] and r["item"].occurrence_date >= today
    ]
    next_day = min((r["item"].occurrence_date for r in future_pending), default=None)
    next_group = [r for r in future_pending if r["item"].occurrence_date == next_day]
    coverage = (
        None
        if difference is None or current is None
        else (
            Decimal(100)
            if due_total == 0
            else max(ZERO, min(Decimal(100), current / due_total * 100))
        )
    )
    # Forecast rolls from today's actual balance, not a repeated monthly balance.
    cash_months = []
    forecast_start = today.replace(day=1)
    rolling = current
    eligible_accounts = {a.id for a in accounts if a.currency == "EUR"}
    for offset in range(6):
        period = forecast_start + relativedelta(months=offset)
        stop = period + relativedelta(months=1)
        outgoing = sum(
            (
                r["pending"]
                for r in rows
                if r["item"].occurrence_date < stop
                and (offset == 0 or r["item"].occurrence_date >= period)
            ),
            ZERO,
        )
        incoming = sum(
            (
                i.amount
                for i in incomes
                if max(today, period) <= i.expected_date < stop
                and i.account_id in eligible_accounts
            ),
            ZERO,
        )
        opening = rolling
        if rolling is not None:
            rolling += incoming - outgoing
        cash_months.append(
            {
                "month": period,
                "opening": opening,
                "income": incoming,
                "pending": outgoing,
                "closing": rolling,
            }
        )
    scale = max(
        (abs(m["closing"]) for m in cash_months if m["closing"] is not None),
        default=Decimal(1),
    ) or Decimal(1)
    for m in cash_months:
        m["width"] = (
            abs(m["closing"]) / scale * 50 if m["closing"] is not None else ZERO
        )
    return {
        "cash_months": cash_months,
        "forecast_income_present": any(m["income"] for m in cash_months),
        "month_end": end,
        "operational_rows": operational,
        "due_total": due_total,
        "difference": difference,
        "coverage": coverage,
        "month_current": start <= today <= end,
        "due_estimated": sum(
            (r["pending"] for r in operational if r["nature"] == "estimated"), ZERO
        ),
        "next_day": next_day,
        "next_count": len(next_group),
        "next_amount": sum((r["pending"] for r in next_group), ZERO),
        "expected_total": sum((i.amount for i in included_income), ZERO),
        "forecast": forecast,
        "graph": graph,
        "next_due": next_due,
        "concentration": concentration,
        "unconfirmed_dates": sum(not r["date_confirmed"] for r in month_rows),
        "rows": month_rows,
        "incomes": incomes,
        "included_income": included_income,
        "overdue_income": any(i.expected_date < today for i in incomes),
        "pending": month_pending,
        "total": total,
        "settled_planned": total - month_pending,
        "overdue": sum(
            (r["pending"] for r in rows if r["item"].occurrence_date < today), ZERO
        ),
        "next_seven": sum(
            (
                r["pending"]
                for r in rows
                if today <= r["item"].occurrence_date <= today + timedelta(days=6)
            ),
            ZERO,
        ),
        "seven_end": today + timedelta(days=6),
        "current": current,
        "projected": running if end >= today else None,
        "timeline": timeline,
        "first_negative": first_negative,
        "realized": received - realized_paid if currencies <= {"EUR"} else None,
        "received": received if currencies <= {"EUR"} else None,
        "realized_paid": realized_paid if currencies <= {"EUR"} else None,
        "confirmed": sum(
            (r["pending"] for r in month_rows if r["nature"] == "confirmed"), ZERO
        ),
        "estimated": sum(
            (r["pending"] for r in month_rows if r["nature"] == "estimated"), ZERO
        ),
        "unclassified": sum(
            (r["pending"] for r in month_rows if r["nature"] == "unclassified"), ZERO
        ),
        "past": end < today,
        "incomplete": incomplete,
        "accounts": [{"account": a, "balance": balances[a.id]} for a in accounts],
    }
