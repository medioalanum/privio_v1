"""FastAPI main application entry point."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models as _models  # noqa: F401 - register tables before create_all
from app.config import settings
from app.database import get_db
from app.routers.commitments import router as commitments_router
from app.routers.deposits import router as deposits_router
from app.routers.web import router as web_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    # Schema changes are explicit operational steps, never inferred payments.
    yield


app = FastAPI(
    title=settings.app_name,
    description="FastAPI Commitment & Recurrence Financial Management API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(commitments_router)
app.include_router(deposits_router)
app.include_router(web_router)


@app.get("/health", tags=["System"], summary="Health check")
def health_check(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    """Health check endpoint to verify service availability."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {
        "commit": os.environ.get("RENDER_GIT_COMMIT", "local"),
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/", tags=["System"], summary="Root endpoint")
def root() -> dict[str, str]:
    """Root endpoint welcoming API consumers and linking to docs."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs_url": "/docs",
        "health_url": "/health",
    }
