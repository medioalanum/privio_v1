"""Database session and connection management using SQLAlchemy."""

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _normalize_database_url(url: str) -> str:
    """Normalize database connection string for psycopg3 driver (handling Neon/Render formats)."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


database_url = _normalize_database_url(settings.database_url)

# Configure SQLite or PostgreSQL connection arguments
connect_args: dict[str, Any] = {}
engine_kwargs: dict[str, Any] = {
    "echo": settings.debug and settings.environment == "development",
}

if database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # Essential for serverless databases like Neon (handles idle disconnects gracefully)
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(
    database_url,
    connect_args=connect_args,
    **engine_kwargs,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models."""

    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency for obtaining a database session per request.

    Yields:
        Session: Active database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
