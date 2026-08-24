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

    EDITOR = "editor"
    VIEWER = "viewer"


class AuthenticatedUser:
    """Represents an authenticated user with a specific role."""

    def __init__(self, username: str, role: Role) -> None:
        self.username = username
        self.role = role


def authenticate_credentials(username: str, password: str) -> AuthenticatedUser | None:
    """Validate a username/password pair against configured accounts."""
    is_editor_user = secrets.compare_digest(username, settings.editor_user)
    is_editor_pass = secrets.compare_digest(password, settings.editor_pass)
    if is_editor_user and is_editor_pass:
        return AuthenticatedUser(username=username, role=Role.EDITOR)

    is_viewer_user = secrets.compare_digest(username, settings.viewer_user)
    is_viewer_pass = secrets.compare_digest(password, settings.viewer_pass)
    if is_viewer_user and is_viewer_pass:
        return AuthenticatedUser(username=username, role=Role.VIEWER)
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
        if not secrets.compare_digest(signature, expected):
            return None
        return AuthenticatedUser(username=username, role=Role(role_value))
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
        AuthenticatedUser with either EDITOR or VIEWER role.

    Raises:
        HTTPException: 401 Unauthorized if credentials do not match.
    """
    session_user = user_from_session(request.cookies.get(SESSION_COOKIE))
    if session_user:
        return session_user

    if credentials:
        basic_user = authenticate_credentials(credentials.username, credentials.password)
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
        basic_user = authenticate_credentials(credentials.username, credentials.password)
        if basic_user:
            return basic_user
    raise HTTPException(
        status_code=status.HTTP_303_SEE_OTHER,
        headers={"Location": f"/login?next={request.url.path}"},
    )


def require_viewer_web(
    user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> AuthenticatedUser:
    """Allow both roles to access browser pages."""
    return user


def require_editor_web(
    user: Annotated[AuthenticatedUser, Depends(require_web_user)],
) -> AuthenticatedUser:
    """Require the editor role for browser mutations."""
    if user.role != Role.EDITOR:
        raise HTTPException(status_code=403, detail="Editor role required")
    return user


def require_viewer(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """Allow access to both Viewer and Editor roles."""
    return user


def require_editor(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AuthenticatedUser:
    """Enforce Editor role, rejecting Viewer with HTTP 403 Forbidden.

    Args:
        user: The authenticated user from credentials.

    Returns:
        AuthenticatedUser if role is EDITOR.

    Raises:
        HTTPException: 403 Forbidden if user is only a VIEWER.
    """
    if user.role != Role.EDITOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Editor role required to perform modifications",
        )
    return user
