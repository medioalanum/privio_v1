"""REST API endpoints for Commitment management and financial projections."""

from collections.abc import Sequence
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, require_editor, require_viewer
from app.database import get_db
from app.models.commitment import Commitment, RecurrenceEnum, StatusEnum
from app.schemas.commitment import (
    CommitmentCreate,
    CommitmentOccurrenceResponse,
    CommitmentResponse,
    CommitmentUpdate,
    SuggestedMonthlyResponse,
)
from app.services.recurrence import (
    calculate_suggested_monthly,
    resolve_upcoming_occurrences,
)

router = APIRouter(tags=["Commitments"])


@router.post(
    "/commitments",
    response_model=CommitmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new commitment",
)
def create_commitment(
    payload: CommitmentCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_editor)],
) -> Commitment:
    """Create a new financial commitment record (Editor role required)."""
    commitment = Commitment(**payload.model_dump())
    db.add(commitment)
    db.commit()
    db.refresh(commitment)
    return commitment


@router.get(
    "/commitments",
    response_model=list[CommitmentResponse],
    summary="List all commitments",
)
def list_commitments(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_viewer)],
    category: Annotated[str | None, Query(description="Filter by category")] = None,
    status_filter: Annotated[
        StatusEnum | None, Query(alias="status", description="Filter by status")
    ] = None,
    recurrence: Annotated[
        RecurrenceEnum | None, Query(description="Filter by recurrence type")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Max items to return")] = 100,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
) -> Sequence[Commitment]:
    """Retrieve commitments with optional filtering and pagination (Viewer or Editor required)."""
    query = select(Commitment)
    if category is not None:
        query = query.where(Commitment.category == category)
    if status_filter is not None:
        query = query.where(Commitment.status == status_filter)
    if recurrence is not None:
        query = query.where(Commitment.recurrence == recurrence)

    query = (
        query.order_by(Commitment.due_date.asc(), Commitment.id.asc())
        .offset(offset)
        .limit(limit)
    )
    return db.scalars(query).all()


@router.get(
    "/upcoming",
    response_model=list[CommitmentOccurrenceResponse],
    summary="List upcoming commitment occurrences",
)
@router.get(
    "/commitments/upcoming",
    response_model=list[CommitmentOccurrenceResponse],
    include_in_schema=False,
)
def get_upcoming_commitments(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_viewer)],
    days: Annotated[
        int, Query(ge=1, le=3650, description="Number of days in the future to project")
    ] = 30,
    from_date: Annotated[
        date | None, Query(description="Base start date (defaults to today)")
    ] = None,
) -> list[CommitmentOccurrenceResponse]:
    """Generate upcoming occurrences for all commitments within the next N days (Viewer or Editor required).

    Handles recurrence for weekly, monthly, semiannual, and annual commitments.
    """
    base_date = from_date or date.today()
    commitments = db.scalars(select(Commitment)).all()
    return resolve_upcoming_occurrences(commitments, from_date=base_date, days=days)


@router.get(
    "/suggested-monthly",
    response_model=SuggestedMonthlyResponse,
    summary="Get suggested monthly budget",
)
@router.get(
    "/commitments/suggested-monthly",
    response_model=SuggestedMonthlyResponse,
    include_in_schema=False,
)
def get_suggested_monthly(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_viewer)],
    only_active: Annotated[
        bool, Query(description="Include only pending commitments")
    ] = True,
) -> SuggestedMonthlyResponse:
    """Calculate suggested monthly amount: monthly + (annual / 12) + (semiannual / 6)."""
    commitments = db.scalars(select(Commitment)).all()
    return calculate_suggested_monthly(commitments, only_active=only_active)


@router.get(
    "/commitments/{commitment_id}",
    response_model=CommitmentResponse,
    summary="Get commitment by ID",
)
def get_commitment(
    commitment_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_viewer)],
) -> Commitment:
    """Retrieve a specific commitment by its identifier (Viewer or Editor required)."""
    commitment = db.get(Commitment, commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commitment with id {commitment_id} not found",
        )
    return commitment


@router.put(
    "/commitments/{commitment_id}",
    response_model=CommitmentResponse,
    summary="Update a commitment (full replacement)",
)
def update_commitment(
    commitment_id: int,
    payload: CommitmentCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_editor)],
) -> Commitment:
    """Fully update an existing commitment (Editor role required)."""
    commitment = db.get(Commitment, commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commitment with id {commitment_id} not found",
        )

    for field, value in payload.model_dump().items():
        setattr(commitment, field, value)

    db.commit()
    db.refresh(commitment)
    return commitment


@router.patch(
    "/commitments/{commitment_id}",
    response_model=CommitmentResponse,
    summary="Partial update a commitment",
)
def patch_commitment(
    commitment_id: int,
    payload: CommitmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_editor)],
) -> Commitment:
    """Partially update specific fields of an existing commitment (Editor role required)."""
    commitment = db.get(Commitment, commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commitment with id {commitment_id} not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(commitment, field, value)

    db.commit()
    db.refresh(commitment)
    return commitment


@router.delete(
    "/commitments/{commitment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a commitment",
)
def delete_commitment(
    commitment_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_editor)],
) -> None:
    """Delete a commitment by ID (Editor role required)."""
    commitment = db.get(Commitment, commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commitment with id {commitment_id} not found",
        )
    db.delete(commitment)
    db.commit()
