"""Authentication and role-based access control for API and browser sessions."""

import base64
import hashlib
import hmac
import secrets
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

security = HTTPBasic(auto_error=False)
SESSION_COOKIE = "privio_session"


class Role(StrEnum):
    """User authorization roles."""

    ADMIN = "admin"
    CLIENT = "client"

    @property
    def label(self) -> str:
        return "Admin" if self == Role.ADMIN else "Client"


class AuthenticatedUser:
    """Represents an authenticated user with a specific role."""

    def __init__(self, username: str, role: Role) -> None:
        self.username = username
        self.role = role


def authenticate_credentials(username: str, password: str) -> AuthenticatedUser | None:
    """Validate a username/password pair against configured accounts."""
    is_admin_user = secrets.compare_digest(
        username.encode(), settings.admin_user.encode()
    )
    is_admin_pass = secrets.compare_digest(
        password.encode(), settings.admin_pass.encode()
    )
    if is_admin_user and is_admin_pass:
        return AuthenticatedUser(username=username, role=Role.ADMIN)

    is_client_user = secrets.compare_digest(
        username.encode(), settings.client_user.encode()
    )
    is_client_pass = secrets.compare_digest(
        password.encode(), settings.client_pass.encode()
    )
    if is_client_user and is_client_pass:
        return AuthenticatedUser(username=username, role=Role.CLIENT)
    return None


def create_session_token(user: AuthenticatedUser) -> str:
    """Create a signed, URL-safe session token without storing credentials."""
    payload = f"{user.username}:{user.role.value}"
    signature = hmac.new(
        settings.session_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()


def user_from_session(token: str | None) -> AuthenticatedUser | None:
    """Verify a browser session token and return its user."""
    if not token:
        return None
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        username, role_value, signature = decoded.rsplit(":", 2)
        payload = f"{username}:{role_value}"
        expected = hmac.new(
            settings.session_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not secrets.compare_digest(signature.encode(), expected.encode()):
            return None
        role = Role(role_value)
        configured_name = (
            settings.admin_user if role == Role.ADMIN else settings.client_user
        )
        if not secrets.compare_digest(username.encode(), configured_name.encode()):
            return None
        return AuthenticatedUser(username=username, role=role)
    except (ValueError, UnicodeDecodeError):
        return None


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPBasicCredentials | None, Depends(security)],
) -> AuthenticatedUser:
    """Authenticate using a signed browser cookie or HTTP Basic credentials.

    Args:
        credentials: Submitted HTTP Basic authentication credentials.

    Returns:
        AuthenticatedUser with either ADMIN or CLIENT role.

    Raises:
        HTTPException: 401 Unauthorized if credentials do not match.
    """
    session_user = user_from_session(request.cookies.get(SESSION_COOKIE))
    if session_user:
        return session_user

    if credentials:
        basic_user = authenticate_credentials(
            credentials.username, credentials.password
        )
        if basic_user:
            return basic_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Basic"},
    )


def require_web_user(
    request: Request,
    credentials: Annotated[HTTPBasicCredentials | None, Depends(security)],
) -> AuthenticatedUser:
    """Require a browser session and redirect anonymous visitors to login."""
    user = user_from_session(request.cookies.get(SESSION_COOKIE))
    if user:
        return user
    if credentials:
        basic_user = authenticate_credentials(
            credentials.username, credentials.password
        )
        if basic_user:
            return basic_user
    raise HTTPException(
        status_code=status.HTTP_303_SEE_OTHER,
        headers={"Location": f"/login?next={request.url.path}"},
    )


def require_authenticated_web(
    user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> AuthenticatedUser:
    """Allow both roles to access browser pages."""
    return user


def require_admin_web(
    user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> AuthenticatedUser:
    """Require the admin role for browser mutations."""
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def require_authenticated(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """Allow access to both Client and Admin roles."""
    return user


def require_admin(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """Enforce Admin role, rejecting Client with HTTP 403 Forbidden.

    Args:
        user: The authenticated user from credentials.

    Returns:
        AuthenticatedUser if role is ADMIN.

    Raises:
        HTTPException: 403 Forbidden if user is only a CLIENT.
    """
    if user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin role required to perform modifications",
        )
    return user
