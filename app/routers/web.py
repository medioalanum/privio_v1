"""Web router serving server-rendered Jinja2 HTML templates and HTMX partials with i18n & RBAC."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import (
    SESSION_COOKIE,
    AuthenticatedUser,
    authenticate_credentials,
    create_session_token,
    require_editor_web,
    require_viewer_web,
)
from app.config import settings
from app.database import get_db
from app.i18n import get_translations, normalize_lang, t
from app.models.commitment import (
    Commitment,
    CommitmentAdjustment,
    RecurrenceEnum,
    StatusEnum,
)
from app.models.deposit import Deposit
from app.services.recurrence import (
    calculate_suggested_monthly,
    resolve_upcoming_occurrences,
)
from app.services.reserve import calculate_reserve_balance

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(include_in_schema=False)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next_path: str = "/") -> Response:
    """Render the branded browser login page."""
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"request": request, "error": None, "next_path": next_path},
    )


@router.post("/login", response_class=HTMLResponse)
def login_action(
    request: Request,
    role: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next_path: Annotated[str, Form()] = "/",
) -> Response:
    """Validate credentials and establish a secure browser session."""
    username = settings.editor_user if role == "editor" else settings.viewer_user
    user = authenticate_credentials(username, password)
    safe_next = (
        next_path
        if next_path.startswith("/") and not next_path.startswith("//")
        else "/"
    )
    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "request": request,
                "error": "Usuário ou senha incorretos.",
                "next_path": safe_next,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    response = RedirectResponse(url=safe_next, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user),
        max_age=60 * 60 * 12,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
    )
    return response


@router.post("/logout")
def logout_action() -> Response:
    """End the current browser session."""
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE)
    return response


def _get_dashboard_context(
    request: Request,
    db: Session,
    user: AuthenticatedUser,
    days: int = 30,
    lang: str = "pt",
    toast_message: str | None = None,
) -> dict[str, object]:
    """Helper to assemble full context needed to render dashboard or its partial."""
    today = date.today()
    lang_code = normalize_lang(lang)
    commitments: Sequence[Commitment] = db.scalars(
        select(Commitment).order_by(Commitment.due_date.asc(), Commitment.id.asc())
    ).all()

    suggested = calculate_suggested_monthly(commitments)
    reserve = calculate_reserve_balance(db)
    month_start = today.replace(day=1)
    occurrences = resolve_upcoming_occurrences(
        commitments, from_date=month_start, days=days
    )
    for occurrence in occurrences:
        occurrence.days_until = (occurrence.occurrence_date - today).days

    return {
        "request": request,
        "user": user,
        "today": today,
        "days": days,
        "lang": lang_code,
        "t": lambda key, **kwargs: t(key, lang=lang_code, **kwargs),
        "translations": get_translations(lang_code),
        "suggested": suggested,
        "reserve": reserve,
        "occurrences": occurrences,
        "commitments": commitments,
        "toast_message": toast_message,
    }


@router.get("/", response_class=HTMLResponse)
def index_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_viewer_web)],
    lang: Annotated[str | None, Query(description="Language code (pt/en/it)")] = None,
) -> Response:
    """Render the main dashboard server-rendered page."""
    lang_code = normalize_lang(lang)
    context = _get_dashboard_context(request, db, user=user, days=30, lang=lang_code)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=context,
    )


@router.get("/ui/upcoming", response_class=HTMLResponse)
def get_upcoming_partial(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_viewer_web)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Render the upcoming commitments partial table for 30/60/90 days."""
    today = date.today()
    lang_code = normalize_lang(lang)
    commitments = db.scalars(select(Commitment)).all()
    month_start = today.replace(day=1)
    occurrences = resolve_upcoming_occurrences(
        commitments, from_date=month_start, days=days
    )
    for occurrence in occurrences:
        occurrence.days_until = (occurrence.occurrence_date - today).days

    return templates.TemplateResponse(
        request=request,
        name="partials/upcoming_table.html",
        context={
            "request": request,
            "user": user,
            "occurrences": occurrences,
            "days": days,
            "lang": lang_code,
            "t": lambda key, **kwargs: t(key, lang=lang_code, **kwargs),
            "today": today,
        },
    )


@router.get("/ui/commitments/new", response_class=HTMLResponse)
def new_commitment_form(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_web)],
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Render the modal form for creating a new commitment."""
    lang_code = normalize_lang(lang)
    return templates.TemplateResponse(
        request=request,
        name="partials/commitment_form.html",
        context={
            "request": request,
            "user": user,
            "commitment": None,
            "lang": lang_code,
            "t": lambda key, **kwargs: t(key, lang=lang_code, **kwargs),
            "today": date.today(),
        },
    )


@router.get("/ui/commitments/{commitment_id}/edit", response_class=HTMLResponse)
def edit_commitment_form(
    request: Request,
    commitment_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_viewer_web)],
    occurrence_date: Annotated[date | None, Query()] = None,
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Render the modal form for editing an existing commitment."""
    commitment = db.get(Commitment, commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Commitment not found"
        )

    lang_code = normalize_lang(lang)
    return templates.TemplateResponse(
        request=request,
        name="partials/commitment_form.html",
        context={
            "request": request,
            "user": user,
            "commitment": commitment,
            "occurrence_date": occurrence_date or commitment.due_date,
            "lang": lang_code,
            "t": lambda key, **kwargs: t(key, lang=lang_code, **kwargs),
            "today": date.today(),
        },
    )


@router.post("/ui/commitments", response_class=HTMLResponse)
def create_commitment_form_action(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    description: Annotated[str, Form()],
    amount: Annotated[Decimal, Form()],
    due_date: Annotated[date, Form()],
    category: Annotated[str, Form()],
    recurrence: Annotated[RecurrenceEnum, Form()] = RecurrenceEnum.NONE,
    status_val: Annotated[StatusEnum, Form(alias="status")] = StatusEnum.PENDING,
    is_estimate: Annotated[bool, Form()] = False,
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Handle commitment creation from HTMX form and return updated dashboard partial."""
    lang_code = normalize_lang(lang)
    commitment = Commitment(
        description=description,
        amount=amount,
        due_date=due_date,
        category=category,
        recurrence=recurrence,
        status=status_val,
        is_estimate=is_estimate,
    )
    db.add(commitment)
    db.commit()

    toast = t("msg_commitment_created", lang=lang_code, desc=description)
    context = _get_dashboard_context(
        request,
        db,
        user=user,
        days=30,
        lang=lang_code,
        toast_message=toast,
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_content.html",
        context=context,
    )


@router.post("/ui/commitments/{commitment_id}/edit", response_class=HTMLResponse)
def update_commitment_form_action(
    request: Request,
    commitment_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    description: Annotated[str, Form()],
    amount: Annotated[Decimal, Form()],
    due_date: Annotated[date, Form()],
    category: Annotated[str, Form()],
    recurrence: Annotated[RecurrenceEnum, Form()] = RecurrenceEnum.NONE,
    status_val: Annotated[StatusEnum, Form(alias="status")] = StatusEnum.PENDING,
    is_estimate: Annotated[bool, Form()] = False,
    scope: Annotated[str, Form()] = "series",
    occurrence_date: Annotated[date | None, Form()] = None,
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Handle commitment update from HTMX form and return updated dashboard partial."""
    lang_code = normalize_lang(lang)
    commitment = db.get(Commitment, commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Commitment not found"
        )

    if scope == "series" or occurrence_date is None:
        commitment.description = description
        commitment.amount = amount
        commitment.due_date = due_date
        commitment.category = category
        commitment.recurrence = recurrence
        commitment.status = status_val
        commitment.is_estimate = is_estimate
    else:
        adjustment = db.scalar(
            select(CommitmentAdjustment).where(
                CommitmentAdjustment.commitment_id == commitment_id,
                CommitmentAdjustment.effective_date == occurrence_date,
                CommitmentAdjustment.scope == scope,
            )
        )
        if adjustment is None:
            adjustment = CommitmentAdjustment(
                commitment_id=commitment_id,
                effective_date=occurrence_date,
                scope=scope,
            )
            db.add(adjustment)
        adjustment.description = description
        adjustment.amount = amount
        adjustment.adjusted_date = due_date if scope == "single" else None
        adjustment.category = category
        adjustment.status = status_val
        adjustment.is_estimate = is_estimate
        adjustment.is_deleted = False

    db.commit()

    if scope == "single" and occurrence_date is not None:
        toast = f"{description}: ocorrência de {occurrence_date:%d/%m/%Y} atualizada."
    elif scope == "future" and occurrence_date is not None:
        toast = (
            f"{description}: série atualizada a partir de {occurrence_date:%d/%m/%Y}."
        )
    else:
        toast = t("msg_commitment_updated", lang=lang_code, desc=description)
    context = _get_dashboard_context(
        request,
        db,
        user=user,
        days=30,
        lang=lang_code,
        toast_message=toast,
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_content.html",
        context=context,
    )


@router.post("/ui/commitments/{commitment_id}/toggle-paid", response_class=HTMLResponse)
def toggle_commitment_status(
    request: Request,
    commitment_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Toggle commitment status between pending and paid."""
    lang_code = normalize_lang(lang)
    commitment = db.get(Commitment, commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Commitment not found"
        )

    if commitment.status == StatusEnum.PAID:
        commitment.status = StatusEnum.PENDING
        msg = t("msg_status_reopened", lang=lang_code, desc=commitment.description)
    else:
        commitment.status = StatusEnum.PAID
        msg = t("msg_status_paid", lang=lang_code, desc=commitment.description)

    db.commit()

    context = _get_dashboard_context(
        request, db, user=user, days=30, lang=lang_code, toast_message=msg
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_content.html",
        context=context,
    )


@router.delete("/ui/commitments/{commitment_id}", response_class=HTMLResponse)
def delete_commitment_action(
    request: Request,
    commitment_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Delete commitment via HTMX and return updated dashboard partial."""
    lang_code = normalize_lang(lang)
    commitment = db.get(Commitment, commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Commitment not found"
        )

    desc = commitment.description
    db.delete(commitment)
    db.commit()

    toast = t("msg_commitment_deleted", lang=lang_code, desc=desc)
    context = _get_dashboard_context(
        request,
        db,
        user=user,
        days=30,
        lang=lang_code,
        toast_message=toast,
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_content.html",
        context=context,
    )


@router.delete(
    "/ui/commitments/{commitment_id}/occurrences/{occurrence_date}",
    response_class=HTMLResponse,
)
def delete_commitment_occurrence(
    request: Request,
    commitment_id: int,
    occurrence_date: date,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Delete one projected occurrence while preserving the recurring series."""
    commitment = db.get(Commitment, commitment_id)
    if commitment is None:
        raise HTTPException(status_code=404, detail="Commitment not found")
    adjustment = db.scalar(
        select(CommitmentAdjustment).where(
            CommitmentAdjustment.commitment_id == commitment_id,
            CommitmentAdjustment.effective_date == occurrence_date,
            CommitmentAdjustment.scope == "single",
        )
    )
    if adjustment is None:
        adjustment = CommitmentAdjustment(
            commitment_id=commitment_id,
            effective_date=occurrence_date,
            scope="single",
        )
        db.add(adjustment)
    adjustment.is_deleted = True
    db.commit()
    lang_code = normalize_lang(lang)
    context = _get_dashboard_context(
        request,
        db,
        user=user,
        days=30,
        lang=lang_code,
        toast_message=f"Ocorrência de {occurrence_date:%d/%m/%Y} excluída.",
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_content.html",
        context=context,
    )


@router.get("/ui/deposits/new", response_class=HTMLResponse)
def new_deposit_form(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_viewer_web)],
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Render the modal form for registering a new deposit."""
    lang_code = normalize_lang(lang)
    return templates.TemplateResponse(
        request=request,
        name="partials/deposit_form.html",
        context={
            "request": request,
            "user": user,
            "lang": lang_code,
            "t": lambda key, **kwargs: t(key, lang=lang_code, **kwargs),
            "today": date.today(),
        },
    )


@router.post("/ui/deposits", response_class=HTMLResponse)
def create_deposit_form_action(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    amount: Annotated[Decimal, Form()],
    date_val: Annotated[date, Form(alias="date")],
    note: Annotated[str | None, Form()] = None,
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Handle deposit submission from HTMX and return updated dashboard partial."""
    lang_code = normalize_lang(lang)
    deposit = Deposit(
        amount=amount,
        date=date_val,
        note=note if note else None,
    )
    db.add(deposit)
    db.commit()

    toast = t("msg_deposit_created", lang=lang_code, amount=f"{amount:,.2f}")
    context = _get_dashboard_context(
        request,
        db,
        user=user,
        days=30,
        lang=lang_code,
        toast_message=toast,
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_content.html",
        context=context,
    )
