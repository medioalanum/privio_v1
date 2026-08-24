"""Pytest configuration and test database fixtures."""

import base64
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - Register models with Base.metadata
from app.config import settings
from app.database import Base, get_db
from app.main import app as fastapi_app

# In-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _get_basic_auth_header(username: str, password: str) -> dict[str, str]:
    """Generate Basic Auth header."""
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create fresh database tables for each test and provide a session."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Default test client with Editor role authentication."""

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    auth_headers = _get_basic_auth_header(settings.editor_user, settings.editor_pass)
    with TestClient(
        fastapi_app, headers=auth_headers, raise_server_exceptions=True
    ) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def editor_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client authenticated as Editor."""

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    auth_headers = _get_basic_auth_header(settings.editor_user, settings.editor_pass)
    with TestClient(
        fastapi_app, headers=auth_headers, raise_server_exceptions=True
    ) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def viewer_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client authenticated as Viewer."""

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    auth_headers = _get_basic_auth_header(settings.viewer_user, settings.viewer_pass)
    with TestClient(
        fastapi_app, headers=auth_headers, raise_server_exceptions=True
    ) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def unauth_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client with no authentication headers."""

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app, raise_server_exceptions=False) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
