"""FastAPI main application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers.commitments import router as commitments_router
from app.routers.deposits import router as deposits_router
from app.routers.web import router as web_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    # Attempt to create tables on startup if database is reachable
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        # Fallback if DB is not immediately available or when running unit test suites
        pass
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
def health_check() -> dict[str, str]:
    """Health check endpoint to verify service availability."""
    return {
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
