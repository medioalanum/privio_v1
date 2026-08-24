"""REST API endpoints for Deposit management and reserve balance calculations."""

from collections.abc import Sequence
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, require_editor, require_viewer
from app.database import get_db
from app.models.deposit import Deposit
from app.schemas.deposit import (
    DepositCreate,
    DepositResponse,
    DepositUpdate,
    ReserveBalanceResponse,
)
from app.services.reserve import calculate_reserve_balance

router = APIRouter(tags=["Deposits & Reserve"])


@router.post(
    "/deposits",
    response_model=DepositResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new deposit",
)
def create_deposit(
    payload: DepositCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_editor)],
) -> Deposit:
    """Register a new funds transfer / deposit (Editor role required)."""
    deposit = Deposit(**payload.model_dump())
    db.add(deposit)
    db.commit()
    db.refresh(deposit)
    return deposit


@router.get(
    "/deposits",
    response_model=list[DepositResponse],
    summary="List all deposits",
)
def list_deposits(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_viewer)],
    start_date: Annotated[
        date | None, Query(description="Filter deposits on or after this date")
    ] = None,
    end_date: Annotated[
        date | None, Query(description="Filter deposits on or before this date")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Max items to return")] = 100,
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
) -> Sequence[Deposit]:
    """Retrieve all deposits with optional date filtering and pagination (Viewer or Editor required)."""
    query = select(Deposit)
    if start_date is not None:
        query = query.where(Deposit.date >= start_date)
    if end_date is not None:
        query = query.where(Deposit.date <= end_date)

    query = (
        query.order_by(Deposit.date.desc(), Deposit.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return db.scalars(query).all()


@router.get(
    "/reserve-balance",
    response_model=ReserveBalanceResponse,
    summary="Get reserve balance",
)
@router.get(
    "/deposits/reserve-balance",
    response_model=ReserveBalanceResponse,
    include_in_schema=False,
)
def get_reserve_balance(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_viewer)],
) -> ReserveBalanceResponse:
    """Calculate the reserve balance: total deposits minus total paid commitments (Viewer or Editor required)."""
    return calculate_reserve_balance(db)


@router.get(
    "/deposits/{deposit_id}",
    response_model=DepositResponse,
    summary="Get deposit by ID",
)
def get_deposit(
    deposit_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_viewer)],
) -> Deposit:
    """Retrieve a specific deposit record by ID (Viewer or Editor required)."""
    deposit = db.get(Deposit, deposit_id)
    if deposit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deposit with id {deposit_id} not found",
        )
    return deposit


@router.put(
    "/deposits/{deposit_id}",
    response_model=DepositResponse,
    summary="Update a deposit (full replacement)",
)
def update_deposit(
    deposit_id: int,
    payload: DepositCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_editor)],
) -> Deposit:
    """Fully update an existing deposit record (Editor role required)."""
    deposit = db.get(Deposit, deposit_id)
    if deposit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deposit with id {deposit_id} not found",
        )

    for field, value in payload.model_dump().items():
        setattr(deposit, field, value)

    db.commit()
    db.refresh(deposit)
    return deposit


@router.patch(
    "/deposits/{deposit_id}",
    response_model=DepositResponse,
    summary="Partial update a deposit",
)
def patch_deposit(
    deposit_id: int,
    payload: DepositUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_editor)],
) -> Deposit:
    """Partially update specific fields of a deposit record (Editor role required)."""
    deposit = db.get(Deposit, deposit_id)
    if deposit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deposit with id {deposit_id} not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deposit, field, value)

    db.commit()
    db.refresh(deposit)
    return deposit


@router.delete(
    "/deposits/{deposit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a deposit",
)
def delete_deposit(
    deposit_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[AuthenticatedUser, Depends(require_editor)],
) -> None:
    """Delete a deposit record by ID (Editor role required)."""
    deposit = db.get(Deposit, deposit_id)
    if deposit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deposit with id {deposit_id} not found",
        )
    db.delete(deposit)
    db.commit()
