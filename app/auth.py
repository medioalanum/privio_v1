"""HTTP Basic Authentication and Role-Based Access Control (RBAC)."""

import secrets
from enum import StrEnum
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

security = HTTPBasic()


class Role(StrEnum):
    """User authorization roles."""

    EDITOR = "editor"
    VIEWER = "viewer"


class AuthenticatedUser:
    """Represents an authenticated user with a specific role."""

    def __init__(self, username: str, role: Role) -> None:
        self.username = username
        self.role = role


def get_current_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
) -> AuthenticatedUser:
    """Validate HTTP Basic credentials against configured editor and viewer credentials.

    Args:
        credentials: Submitted HTTP Basic authentication credentials.

    Returns:
        AuthenticatedUser with either EDITOR or VIEWER role.

    Raises:
        HTTPException: 401 Unauthorized if credentials do not match.
    """
    # Check Editor credentials
    is_editor_user = secrets.compare_digest(credentials.username, settings.editor_user)
    is_editor_pass = secrets.compare_digest(credentials.password, settings.editor_pass)
    if is_editor_user and is_editor_pass:
        return AuthenticatedUser(username=credentials.username, role=Role.EDITOR)

    # Check Viewer credentials
    is_viewer_user = secrets.compare_digest(credentials.username, settings.viewer_user)
    is_viewer_pass = secrets.compare_digest(credentials.password, settings.viewer_pass)
    if is_viewer_user and is_viewer_pass:
        return AuthenticatedUser(username=credentials.username, role=Role.VIEWER)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Basic"},
    )


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
