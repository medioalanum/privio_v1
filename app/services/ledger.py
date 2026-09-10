"""Read-only movement history. Never infer an account for unassigned entries."""

from datetime import date
from decimal import Decimal
from typing import NotRequired, TypedDict

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.commitment import Commitment
from app.models.deposit import Deposit
from app.models.financial_account import AccountTransfer, FinancialAccount
from app.models.payment import Payment


class LedgerRow(TypedDict):
    id: str
    date: date
    kind: str
    description: str
    amount: Decimal
    account_id: int | None
    order: int
    balance: NotRequired[Decimal | None]
    account: NotRequired[FinancialAccount | None]


def ledger_rows(
    db: Session, month: date, today: date, account_filter: str | None
) -> list[LedgerRow]:
    accounts = {a.id: a for a in db.scalars(select(FinancialAccount))}
    descriptions = {c.id: c.description for c in db.scalars(select(Commitment))}
    rows: list[LedgerRow] = []
    for d in db.scalars(select(Deposit)):
        rows.append(
            {
                "id": f"deposit-{d.id}",
                "date": d.date,
                "kind": "movement_income",
                "description": d.note or "",
                "amount": d.amount,
                "account_id": d.account_id,
                "order": 0,
            }
        )
    for p in db.scalars(select(Payment)):
        rows.append(
            {
                "id": f"payment-{p.id}",
                "date": p.payment_date,
                "kind": "movement_payment",
                "description": descriptions[p.commitment_id],
                "amount": -p.paid_amount,
                "account_id": p.account_id,
                "order": 1,
            }
        )
    for transfer in db.scalars(select(AccountTransfer)):
        for aid, sign in [(transfer.from_account_id, -1), (transfer.to_account_id, 1)]:
            rows.append(
                {
                    "id": f"transfer-{transfer.id}-{aid}",
                    "date": transfer.date,
                    "kind": "movement_transfer",
                    "description": transfer.note or "",
                    "amount": transfer.amount * sign,
                    "account_id": aid,
                    "order": 2,
                }
            )
    balances = {aid: Decimal(a.opening_balance) for aid, a in accounts.items()}
    result = []
    end = month + relativedelta(months=1)
    for row in sorted(
        rows, key=lambda r: (r["date"], r["order"], int(r["id"].split("-")[1]))
    ):
        aid = row["account_id"]
        if row["date"] > today:
            continue
        if aid in balances:
            balances[aid] += row["amount"]
        row["balance"] = balances.get(aid)
        row["account"] = accounts.get(aid)
        if month <= row["date"] < end and (
            not account_filter or str(aid or "unassigned") == account_filter
        ):
            result.append(row)
    return result
