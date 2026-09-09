"""Authenticated download of a transient monthly snapshot."""

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.auth import AuthenticatedUser, require_authenticated_web
from app.config import settings
from app.database import get_db
from app.i18n import normalize_lang
from app.services.monthly_report import monthly_data, render_monthly_pdf

router = APIRouter()


@router.get("/reports/monthly.pdf", include_in_schema=False)
def monthly_report(
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_web)],
    db: Annotated[Session, Depends(get_db)],
    month: Annotated[str, Query(pattern=r"^\d{4}-\d{2}$")],
    lang: str = "pt",
) -> Response:
    try:
        selected = date.fromisoformat(month + "-01")
        # Existing recurrence projection looks one year ahead.
        if not 1900 <= selected.year <= 9997:
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid report month") from None
    exported = datetime.now(UTC)
    data = monthly_data(db, selected, exported.date())
    pdf = render_monthly_pdf(
        data, selected, exported, normalize_lang(lang), demo=settings.demo_mode
    )
    filename = f"Privio_{month}_exportado_{exported:%Y-%m-%d}.pdf"
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )
