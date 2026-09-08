"""Web router serving server-rendered Jinja2 HTML templates and HTMX partials with i18n & RBAC."""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from dateutil.relativedelta import relativedelta
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
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
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
from app.models.financial_account import AccountTransfer, FinancialAccount
from app.models.income import ExpectedIncome
from app.models.payment import Payment
from app.services.decisions import decision_summary
from app.services.recurrence import resolve_upcoming_occurrences
from app.services.reserve import (
    calculate_financial_position,
)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(include_in_schema=False)


def format_money(value: Decimal | None, lang: str = "pt") -> str:
    if value is None:
        return "—"
    formatted = f"{value:,.2f}"
    if lang in {"pt", "it"}:
        formatted = formatted.translate(str.maketrans({",": ".", ".": ","}))
    return f"€ {formatted}"


def _selected_month(request: Request) -> date:
    """Return the requested calendar month, falling back to the current month."""
    raw = request.query_params.get("month")
    if raw:
        try:
            return date.fromisoformat(f"{raw}-01")
        except ValueError:
            pass
    return date.today().replace(day=1)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next_path: str = "/") -> Response:
    """Render the branded browser login page."""
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "request": request,
            "error": None,
            "next_path": next_path,
            "preview_mode": settings.preview_mode,
        },
    )


@router.post("/login", response_class=HTMLResponse)
def login_action(
    request: Request,
    role: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next_path: Annotated[str, Form()] = "/",
) -> Response:
    """Validate credentials and establish a secure browser session."""
    username = {
        "admin": settings.admin_user,
        "client": settings.client_user,
        "editor": settings.editor_user,
        "viewer": settings.viewer_user,
    }.get(role, "")
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
                "preview_mode": settings.preview_mode,
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
    selected_month = _selected_month(request)
    lang_code = normalize_lang(lang)
    commitments: Sequence[Commitment] = db.scalars(
        select(Commitment).order_by(Commitment.due_date.asc(), Commitment.id.asc())
    ).all()

    month_start = selected_month
    decisions = decision_summary(db, commitments, month_start, today)
    accounts = [row["account"] for row in decisions["accounts"]]
    query = request.query_params
    rows = (
        decisions["rows"]
        if query.get("status") == "paid"
        else decisions["operational_rows"]
    )
    categories = sorted({row["item"].category for row in rows})
    filtered = [
        row
        for row in rows
        if (
            not query.get("q")
            or query["q"].casefold()
            in (row["item"].description + " " + row["item"].category).casefold()
        )
        and (not query.get("status") or row["status"] == query["status"])
        and (not query.get("nature") or row["nature"] == query["nature"])
        and (not query.get("category") or row["item"].category == query["category"])
    ]
    if query.get("account"):
        filtered = [
            row
            for row in filtered
            if str(row["payment"].account_id if row["payment"] else "unassigned")
            == query["account"]
        ]
    if query.get("responsible"):
        owned = {a.id for a in accounts if a.responsible == query["responsible"]}
        filtered = [
            row
            for row in filtered
            if row["payment"] and row["payment"].account_id in owned
        ]
    if query.get("sort") == "amount":
        filtered.sort(key=lambda row: row["pending"], reverse=True)
    day_totals = {}
    for row in filtered:
        due = row["item"].occurrence_date
        day_totals[due] = day_totals.get(due, Decimal("0.00")) + row["pending"]
    return {
        "day_totals": day_totals,
        "preview_mode": settings.preview_mode,
        "decision_rows": filtered,
        "filtered_pending": sum((row["pending"] for row in filtered), Decimal("0.00")),
        "categories": categories,
        "responsibles": sorted({a.responsible for a in accounts if a.responsible}),
        "decisions": decisions,
        "money": lambda value: format_money(value, lang_code),
        "request": request,
        "user": user,
        "today": today,
        "days": days,
        "selected_month": selected_month,
        "selected_month_key": selected_month.strftime("%Y-%m"),
        "previous_month_key": (selected_month - relativedelta(months=1)).strftime(
            "%Y-%m"
        ),
        "next_month_key": (selected_month + relativedelta(months=1)).strftime("%Y-%m"),
        "selected_month_label": t(f"month_{selected_month.month}", lang=lang_code)
        + f" {selected_month.year}",
        "lang": lang_code,
        "t": lambda key, **kwargs: t(key, lang=lang_code, **kwargs),
        "translations": get_translations(lang_code),
        "accounts": accounts,
        "forecast": decisions["forecast"],
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
    context = _get_dashboard_context(request, db, user, days, normalize_lang(lang))
    return templates.TemplateResponse(
        request=request, name="partials/upcoming_table.html", context=context
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
            "selected_month_key": _selected_month(request).strftime("%Y-%m"),
        },
    )


@router.get("/ui/commitments/{commitment_id}/edit", response_class=HTMLResponse)
def edit_commitment_form(
    request: Request,
    commitment_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_viewer_web)],
    occurrence_date: Annotated[date | None, Query()] = None,
    scope: Annotated[str, Query(pattern="^(single|series)$")] = "single",
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Render the modal form for editing an existing commitment."""
    commitment = db.get(Commitment, commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Commitment not found"
        )

    displayed = (
        next(iter(resolve_upcoming_occurrences([commitment], occurrence_date, 0)), None)
        if occurrence_date and scope != "series"
        else None
    )
    form_commitment = (
        {**displayed.model_dump(), "id": commitment.id} if displayed else commitment
    )
    lang_code = normalize_lang(lang)
    return templates.TemplateResponse(
        request=request,
        name="partials/commitment_form.html",
        context={
            "request": request,
            "user": user,
            "edit_scope": scope,
            "commitment": form_commitment,
            "occurrence_date": occurrence_date or commitment.due_date,
            "lang": lang_code,
            "t": lambda key, **kwargs: t(key, lang=lang_code, **kwargs),
            "today": date.today(),
            "selected_month_key": _selected_month(request).strftime("%Y-%m"),
        },
    )


@router.post("/ui/commitments", response_class=HTMLResponse)
def create_commitment_form_action(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    description: Annotated[str, Form()],
    amount: Annotated[Decimal, Form(gt=0, decimal_places=2, max_digits=12)],
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
    amount: Annotated[Decimal, Form(gt=0, decimal_places=2, max_digits=12)],
    due_date: Annotated[date, Form()],
    category: Annotated[str, Form()],
    recurrence: Annotated[RecurrenceEnum, Form()] = RecurrenceEnum.NONE,
    status_val: Annotated[StatusEnum, Form(alias="status")] = StatusEnum.PENDING,
    is_estimate: Annotated[bool, Form()] = False,
    scope: Annotated[str, Form(pattern="^(single|future|series)$")] = "series",
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
    occurrence_date: Annotated[date | None, Query()] = None,
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Toggle a displayed occurrence, or the base commitment when none is given."""
    lang_code = normalize_lang(lang)
    commitment = db.get(Commitment, commitment_id)
    if commitment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Commitment not found"
        )

    target_status: StatusEnum
    if occurrence_date is not None:
        # A recurring series is a schedule template. Its base status must remain
        # pending; payment/reopening belongs to the selected occurrence.
        if commitment.recurrence != RecurrenceEnum.NONE:
            commitment.status = StatusEnum.PENDING
        displayed = next(
            (
                item
                for item in resolve_upcoming_occurrences(
                    [commitment], from_date=occurrence_date, days=0
                )
                if item.occurrence_date == occurrence_date
            ),
            None,
        )
        current_status = displayed.status if displayed else commitment.status
        target_status = (
            StatusEnum.PENDING if current_status == StatusEnum.PAID else StatusEnum.PAID
        )
        adjustment = db.scalar(
            select(CommitmentAdjustment).where(
                CommitmentAdjustment.commitment_id == commitment_id,
                CommitmentAdjustment.scope == "single",
                or_(
                    CommitmentAdjustment.effective_date == occurrence_date,
                    CommitmentAdjustment.adjusted_date == occurrence_date,
                ),
            )
        )
        if adjustment is None:
            adjustment = CommitmentAdjustment(
                commitment_id=commitment_id,
                effective_date=occurrence_date,
                scope="single",
            )
            db.add(adjustment)
        adjustment.status = target_status
        adjustment.is_deleted = False
    else:
        target_status = (
            StatusEnum.PENDING
            if commitment.status == StatusEnum.PAID
            else StatusEnum.PAID
        )
        commitment.status = target_status

    if target_status == StatusEnum.PENDING:
        msg = t("msg_status_reopened", lang=lang_code, desc=commitment.description)
    else:
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


@router.get("/ui/payments/new", response_class=HTMLResponse)
def new_payment_form(
    request: Request,
    commitment_id: int,
    occurrence_date: date,
    amount: Decimal,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Open the form that records an actual payment for one due date."""
    lang_code = normalize_lang(lang)
    return templates.TemplateResponse(
        request=request,
        name="partials/payment_form.html",
        context={
            "request": request,
            "user": user,
            "commitment_id": commitment_id,
            "occurrence_date": occurrence_date,
            "planned_amount": amount,
            "accounts": db.scalars(
                select(FinancialAccount)
                .where(FinancialAccount.is_active.is_(True))
                .order_by(FinancialAccount.name)
            ).all(),
            "today": date.today(),
            "lang": lang_code,
            "selected_month_key": _selected_month(request).strftime("%Y-%m"),
            "t": lambda key, **kwargs: t(key, lang=lang_code, **kwargs),
        },
    )


@router.post("/ui/payments", response_class=HTMLResponse)
def save_payment(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    commitment_id: Annotated[int, Form()],
    occurrence_date: Annotated[date, Form()],
    payment_date: Annotated[date, Form()],
    planned_amount: Annotated[Decimal, Form(gt=0, decimal_places=2, max_digits=12)],
    paid_amount: Annotated[Decimal, Form(gt=0, decimal_places=2, max_digits=12)],
    account_id: Annotated[int, Form()] = 0,
    note: Annotated[str | None, Form()] = None,
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Create or update payment details without changing the scheduled due date."""
    # Serialize writes on the series; the unique occurrence key is the final guard.
    commitment = db.scalar(
        select(Commitment).where(Commitment.id == commitment_id).with_for_update()
    )
    if commitment is None:
        raise HTTPException(status_code=404, detail="Commitment not found")
    if (
        not paid_amount.is_finite()
        or paid_amount <= 0
        or paid_amount != paid_amount.quantize(Decimal("0.01"))
    ):
        raise HTTPException(status_code=422, detail="Invalid payment amount")
    if payment_date > date.today():
        raise HTTPException(
            status_code=422, detail="Payment date must not be in the future"
        )
    occurrence = next(
        iter(resolve_upcoming_occurrences([commitment], occurrence_date, 0)), None
    )
    if occurrence is None:
        raise HTTPException(status_code=422, detail="Occurrence not found")
    planned_amount = occurrence.amount
    if account_id:
        account = db.scalar(
            select(FinancialAccount)
            .where(FinancialAccount.id == account_id)
            .with_for_update()
        )
        if account is None or not account.is_active or account.currency != "EUR":
            raise HTTPException(status_code=422, detail="Select an active EUR account")
    payment = db.scalar(
        select(Payment).where(
            Payment.commitment_id == commitment_id,
            Payment.occurrence_date == occurrence_date,
        )
    )
    if payment is not None:
        identical = (
            payment.payment_date == payment_date
            and payment.paid_amount == paid_amount
            and payment.account_id == (account_id or None)
            and payment.note == (note or None)
        )
        if not identical:
            raise HTTPException(
                status_code=409,
                detail="Payment already exists; reopen explicitly before changing it",
            )
        return templates.TemplateResponse(
            request=request,
            name="partials/dashboard_content.html",
            context=_get_dashboard_context(
                request, db, user, lang=normalize_lang(lang)
            ),
        )
    if payment is None:
        payment = Payment(
            commitment_id=commitment_id,
            occurrence_date=occurrence_date,
            payment_date=payment_date,
            planned_amount=planned_amount,
            paid_amount=paid_amount,
        )
        db.add(payment)
    payment.payment_date = payment_date
    payment.planned_amount = planned_amount
    payment.paid_amount = paid_amount
    payment.note = note or None
    payment.account_id = account_id or None

    adjustment = db.scalar(
        select(CommitmentAdjustment).where(
            CommitmentAdjustment.commitment_id == commitment_id,
            CommitmentAdjustment.scope == "single",
            or_(
                CommitmentAdjustment.effective_date == occurrence_date,
                CommitmentAdjustment.adjusted_date == occurrence_date,
            ),
        )
    )
    if adjustment is None:
        adjustment = CommitmentAdjustment(
            commitment_id=commitment_id,
            effective_date=occurrence_date,
            scope="single",
        )
        db.add(adjustment)
    adjustment.status = StatusEnum.PAID
    adjustment.is_deleted = False
    if commitment.recurrence != RecurrenceEnum.NONE:
        commitment.status = StatusEnum.PENDING
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Payment already recorded; refresh the dashboard"
        ) from None

    lang_code = normalize_lang(lang)
    context = _get_dashboard_context(
        request,
        db,
        user=user,
        lang=lang_code,
        toast_message=t("msg_payment_saved", lang=lang_code),
    )
    return templates.TemplateResponse(
        request=request, name="partials/dashboard_content.html", context=context
    )


@router.delete(
    "/ui/payments/{commitment_id}/{occurrence_date}", response_class=HTMLResponse
)
def reopen_payment(
    request: Request,
    commitment_id: int,
    occurrence_date: date,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Remove actual payment data and reopen only the selected due date."""
    payment = db.scalar(
        select(Payment).where(
            Payment.commitment_id == commitment_id,
            Payment.occurrence_date == occurrence_date,
        )
    )
    if payment is not None:
        db.delete(payment)
    adjustment = db.scalar(
        select(CommitmentAdjustment).where(
            CommitmentAdjustment.commitment_id == commitment_id,
            CommitmentAdjustment.scope == "single",
            or_(
                CommitmentAdjustment.effective_date == occurrence_date,
                CommitmentAdjustment.adjusted_date == occurrence_date,
            ),
        )
    )
    if adjustment is not None:
        adjustment.status = StatusEnum.PENDING
    db.commit()
    lang_code = normalize_lang(lang)
    context = _get_dashboard_context(
        request,
        db,
        user=user,
        lang=lang_code,
        toast_message=t("msg_payment_reopened", lang=lang_code),
    )
    return templates.TemplateResponse(
        request=request, name="partials/dashboard_content.html", context=context
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
    scope: Annotated[str, Query(pattern="^(single|future)$")] = "single",
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
    adjustment.is_deleted = True
    db.commit()
    lang_code = normalize_lang(lang)
    context = _get_dashboard_context(
        request,
        db,
        user=user,
        days=30,
        lang=lang_code,
        toast_message=(
            f"Vencimentos a partir de {occurrence_date:%d/%m/%Y} excluídos."
            if scope == "future"
            else f"Vencimento de {occurrence_date:%d/%m/%Y} excluído."
        ),
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_content.html",
        context=context,
    )


@router.get("/ui/deposits/new", response_class=HTMLResponse)
def new_deposit_form(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
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
            "selected_month_key": _selected_month(request).strftime("%Y-%m"),
            "accounts": db.scalars(
                select(FinancialAccount)
                .where(FinancialAccount.is_active.is_(True))
                .order_by(FinancialAccount.name)
            ).all(),
        },
    )


@router.get("/ui/accounts/new", response_class=HTMLResponse)
def new_account_form(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Render the account/wallet creation form."""
    lang_code = normalize_lang(lang)
    return templates.TemplateResponse(
        request=request,
        name="partials/account_form.html",
        context={
            "request": request,
            "user": user,
            "lang": lang_code,
            "selected_month_key": _selected_month(request).strftime("%Y-%m"),
            "t": lambda key, **kwargs: t(key, lang=lang_code, **kwargs),
        },
    )


@router.post("/ui/accounts", response_class=HTMLResponse)
def create_account(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    name: Annotated[str, Form()],
    account_type: Annotated[str, Form()],
    responsible: Annotated[str | None, Form()] = None,
    opening_balance: Annotated[Decimal, Form()] = Decimal("0.00"),
    notes: Annotated[str | None, Form()] = None,
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Create a freely named financial account or wallet."""
    if db.scalar(select(FinancialAccount).where(FinancialAccount.name == name)):
        raise HTTPException(status_code=409, detail="Account name already exists")
    db.add(
        FinancialAccount(
            name=name,
            account_type=account_type,
            responsible=responsible or None,
            currency="EUR",
            opening_balance=opening_balance,
            notes=notes or None,
        )
    )
    db.commit()
    lang_code = normalize_lang(lang)
    context = _get_dashboard_context(
        request,
        db,
        user=user,
        lang=lang_code,
        toast_message=t("msg_account_created", lang=lang_code, name=name),
    )
    return templates.TemplateResponse(
        request=request, name="partials/dashboard_content.html", context=context
    )


@router.get("/ui/transfers/new", response_class=HTMLResponse)
def new_transfer_form(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Render the internal transfer form."""
    lang_code = normalize_lang(lang)
    return templates.TemplateResponse(
        request=request,
        name="partials/transfer_form.html",
        context={
            "request": request,
            "user": user,
            "lang": lang_code,
            "selected_month_key": _selected_month(request).strftime("%Y-%m"),
            "today": date.today(),
            "accounts": db.scalars(
                select(FinancialAccount)
                .where(FinancialAccount.is_active.is_(True))
                .order_by(FinancialAccount.name)
            ).all(),
            "t": lambda key, **kwargs: t(key, lang=lang_code, **kwargs),
        },
    )


@router.post("/ui/transfers", response_class=HTMLResponse)
def create_transfer(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    from_account_id: Annotated[int, Form()],
    to_account_id: Annotated[int, Form()],
    amount: Annotated[Decimal, Form(gt=0, decimal_places=2, max_digits=12)],
    transfer_date: Annotated[date, Form()],
    note: Annotated[str | None, Form()] = None,
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Transfer resources without changing the total financial position."""
    if transfer_date > date.today():
        raise HTTPException(
            status_code=422, detail="Transfer date cannot be in the future"
        )
    if from_account_id == to_account_id:
        raise HTTPException(status_code=422, detail="Accounts must be different")
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")
    accounts = db.scalars(
        select(FinancialAccount)
        .where(FinancialAccount.id.in_([from_account_id, to_account_id]))
        .order_by(FinancialAccount.id)
        .with_for_update()
    ).all()
    if len(accounts) != 2 or any(
        not account.is_active or account.currency != "EUR" for account in accounts
    ):
        raise HTTPException(status_code=404, detail="Account not found")
    current_position = calculate_financial_position(db, [], transfer_date)
    source_balance = next(
        account.balance
        for account in current_position.accounts
        if account.id == from_account_id
    )
    if amount > source_balance:
        raise HTTPException(status_code=422, detail="Insufficient account balance")
    db.add(
        AccountTransfer(
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount,
            date=transfer_date,
            note=note or None,
        )
    )
    db.commit()
    lang_code = normalize_lang(lang)
    context = _get_dashboard_context(
        request,
        db,
        user=user,
        lang=lang_code,
        toast_message=t("msg_transfer_created", lang=lang_code),
    )
    return templates.TemplateResponse(
        request=request, name="partials/dashboard_content.html", context=context
    )


@router.post("/ui/deposits", response_class=HTMLResponse)
def create_deposit_form_action(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    amount: Annotated[Decimal, Form(gt=0, decimal_places=2, max_digits=12)],
    date_val: Annotated[date, Form(alias="date")],
    note: Annotated[str | None, Form()] = None,
    account_id: Annotated[int, Form()] = 0,
    expected: Annotated[bool, Form()] = False,
    nature: Annotated[
        str, Form(pattern="^(confirmed|estimated|unclassified)$")
    ] = "unclassified",
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    """Handle deposit submission from HTMX and return updated dashboard partial."""
    lang_code = normalize_lang(lang)
    if (
        not amount.is_finite()
        or amount <= 0
        or amount != amount.quantize(Decimal("0.01"))
    ):
        raise HTTPException(status_code=422, detail="Invalid amount")
    if account_id:
        account = db.get(FinancialAccount, account_id)
        if account is None or not account.is_active or account.currency != "EUR":
            raise HTTPException(status_code=422, detail="Select an active EUR account")
    if expected:
        if not account_id or date_val < date.today():
            raise HTTPException(
                status_code=422,
                detail="Expected income needs an account and a future or current date",
            )
        db.add(
            ExpectedIncome(
                description=note or "Income",
                amount=amount,
                expected_date=date_val,
                nature=nature,
                account_id=account_id,
            )
        )
        db.commit()
        return templates.TemplateResponse(
            request=request,
            name="partials/dashboard_content.html",
            context=_get_dashboard_context(request, db, user, lang=lang_code),
        )
    if date_val > date.today():
        raise HTTPException(
            status_code=422, detail="Use expected income for future dates"
        )
    deposit = Deposit(
        amount=amount,
        date=date_val,
        note=note if note else None,
        account_id=account_id or None,
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


@router.post("/ui/reviews", response_class=HTMLResponse)
def review_occurrence(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    commitment_id: Annotated[int, Form()],
    occurrence_date: Annotated[date, Form()],
    nature: Annotated[str, Form(pattern="^(confirmed|estimated|unclassified)$")],
    date_confirmed: Annotated[bool, Form()] = False,
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    from app.models.review import OccurrenceReview

    commitment = db.scalar(
        select(Commitment).where(Commitment.id == commitment_id).with_for_update()
    )
    if commitment is None or not resolve_upcoming_occurrences(
        [commitment], occurrence_date, 0
    ):
        raise HTTPException(status_code=404, detail="Occurrence not found")
    review = db.scalar(
        select(OccurrenceReview).where(
            OccurrenceReview.commitment_id == commitment_id,
            OccurrenceReview.occurrence_date == occurrence_date,
        )
    )
    if review is None:
        review = OccurrenceReview(
            commitment_id=commitment_id, occurrence_date=occurrence_date
        )
        db.add(review)
    review.reviewed_amount = resolve_upcoming_occurrences(
        [commitment], occurrence_date, 0
    )[0].amount
    review.nature = nature
    review.date_confirmed = date_confirmed
    db.commit()
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_content.html",
        context=_get_dashboard_context(request, db, user, lang=normalize_lang(lang)),
    )


@router.post("/ui/income/{income_id}/receive", response_class=HTMLResponse)
def receive_income(
    request: Request,
    income_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AuthenticatedUser, Depends(require_editor_web)],
    received_date: Annotated[date, Form()],
    received_amount: Annotated[Decimal, Form(gt=0, decimal_places=2)],
    lang: Annotated[str | None, Query()] = None,
) -> Response:
    income = db.scalar(
        select(ExpectedIncome).where(ExpectedIncome.id == income_id).with_for_update()
    )
    if income is None:
        raise HTTPException(status_code=404, detail="Expected income not found")
    if received_date > date.today():
        raise HTTPException(
            status_code=422, detail="Receipt date cannot be in the future"
        )
    if income.deposit_id is None:
        deposit = Deposit(
            amount=received_amount,
            date=received_date,
            account_id=income.account_id,
            note=income.description,
        )
        db.add(deposit)
        db.flush()
        income.deposit_id = deposit.id
        db.commit()
    else:
        deposit = db.get(Deposit, income.deposit_id)
        if (
            deposit is None
            or deposit.amount != received_amount
            or deposit.date != received_date
        ):
            raise HTTPException(status_code=409, detail="Income already received")
    return templates.TemplateResponse(
        request=request,
        name="partials/dashboard_content.html",
        context=_get_dashboard_context(request, db, user, lang=normalize_lang(lang)),
    )
