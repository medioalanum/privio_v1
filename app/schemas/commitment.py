"""Pydantic schemas for request validation and response serialization."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.commitment import RecurrenceEnum, StatusEnum


class CommitmentBase(BaseModel):
    """Base schema attributes for commitments."""

    description: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Brief description of the commitment",
    )
    amount: Decimal = Field(
        ...,
        gt=0,
        decimal_places=2,
        max_digits=12,
        description="Monetary amount (must be positive)",
    )
    is_estimate: bool = Field(
        default=False, description="Flag indicating if the amount is an estimated value"
    )
    due_date: date = Field(..., description="Original due date of the commitment")
    recurrence: RecurrenceEnum = Field(
        default=RecurrenceEnum.NONE, description="Recurrence frequency"
    )
    category: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Category for grouping commitments",
    )
    status: StatusEnum = Field(
        default=StatusEnum.PENDING, description="Current payment status"
    )


class CommitmentCreate(CommitmentBase):
    """Schema for creating a new commitment."""

    pass


class CommitmentUpdate(BaseModel):
    """Schema for updating an existing commitment. All fields are optional."""

    description: str | None = Field(default=None, min_length=1, max_length=255)
    amount: Decimal | None = Field(default=None, gt=0, decimal_places=2, max_digits=12)
    is_estimate: bool | None = None
    due_date: date | None = None
    recurrence: RecurrenceEnum | None = None
    category: str | None = Field(default=None, min_length=1, max_length=100)
    status: StatusEnum | None = None


class CommitmentResponse(CommitmentBase):
    """Schema for returning commitment details."""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommitmentOccurrenceResponse(BaseModel):
    """Schema representing an upcoming occurrence of a commitment."""

    original_commitment_id: int
    description: str
    amount: Decimal
    is_estimate: bool
    original_due_date: date
    occurrence_date: date
    days_until: int
    recurrence: RecurrenceEnum
    category: str
    status: StatusEnum

    model_config = ConfigDict(from_attributes=True)


class SuggestedMonthlyResponse(BaseModel):
    """Schema for the suggested monthly financial breakdown."""

    total_suggested_monthly: Decimal = Field(
        ...,
        description="Total monthly amount: monthly + (annual / 12) + (semiannual / 6)",
    )
    monthly_sum: Decimal = Field(
        ..., description="Direct sum of all active monthly commitments"
    )
    semiannual_sum: Decimal = Field(
        ..., description="Direct sum of all active semiannual commitments"
    )
    semiannual_contribution: Decimal = Field(
        ..., description="Semiannual contribution per month (semiannual_sum / 6)"
    )
    annual_sum: Decimal = Field(
        ..., description="Direct sum of all active annual commitments"
    )
    annual_contribution: Decimal = Field(
        ..., description="Annual contribution per month (annual_sum / 12)"
    )
    active_commitments_count: int = Field(
        ..., description="Total count of active commitments considered"
    )
