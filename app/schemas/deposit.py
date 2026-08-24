"""Pydantic schemas for deposits and reserve balance calculations."""

import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DepositBase(BaseModel):
    """Base schema attributes for deposits."""

    amount: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        max_digits=12,
        description="Monetary amount deposited (positive)",
    )
    date: datetime.date = Field(..., description="Date on which the deposit was made")
    note: str | None = Field(
        default=None,
        max_length=255,
        description="Optional note or reference for the deposit",
    )


class DepositCreate(DepositBase):
    """Schema for creating a new deposit record."""

    pass


class DepositUpdate(BaseModel):
    """Schema for updating a deposit. All fields are optional."""

    amount: Decimal | None = Field(default=None, gt=0, decimal_places=2, max_digits=12)
    date: datetime.date | None = None
    note: str | None = Field(default=None, max_length=255)


class DepositResponse(DepositBase):
    """Schema for returning deposit details."""

    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ReserveBalanceResponse(BaseModel):
    """Schema representing the current reserve balance."""

    total_deposits: Decimal = Field(..., description="Sum of all deposits made")
    total_paid_commitments: Decimal = Field(
        ..., description="Sum of all commitments marked as paid"
    )
    reserve_balance: Decimal = Field(
        ..., description="Net reserve: total deposits minus total paid commitments"
    )
    deposits_count: int = Field(..., description="Total number of deposits registered")
    paid_commitments_count: int = Field(
        ..., description="Total number of paid commitments"
    )


class MonthlyCashFlowResponse(BaseModel):
    """Financial position for the calendar month containing ``month``."""

    month: datetime.date
    received: Decimal
    bills_total: Decimal
    paid: Decimal
    pending: Decimal
    available_now: Decimal
    projected_balance: Decimal
    deposits_count: int
    bills_count: int
    paid_count: int
    pending_count: int


class MonthlyForecastResponse(BaseModel):
    """One row in the 12-month cash requirement forecast."""

    month: datetime.date
    total: Decimal
    paid: Decimal
    pending: Decimal
    status: str
    notable_items: list[str]
