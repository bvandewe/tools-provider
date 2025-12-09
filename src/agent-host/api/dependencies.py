"""FastAPI dependencies for authentication."""

import logging
from typing import Optional

from api.services.auth_service import AuthService
from application.services.chat_service import ChatService
from application.settings import app_settings
from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


def get_auth_service(request: Request) -> AuthService:
    """
    Get AuthService from request state (injected by middleware).

    Args:
        request: FastAPI request

    Returns:
        AuthService instance

    Raises:
        RuntimeError: If AuthService not configured
    """
    auth_service = getattr(request.state, "auth_service", None)
    if auth_service is None:
        raise RuntimeError("AuthService not found. Ensure middleware is configured in app startup.")
    return auth_service


def get_chat_service(request: Request) -> ChatService:
    """
    Get ChatService from scoped service provider.

    ChatService is a scoped service, so it must be resolved from the
    request-scoped service provider, not the root service provider.

    Args:
        request: FastAPI request

    Returns:
        ChatService instance (scoped to request)
    """
    # Get scoped service provider from request state
    scoped_provider = getattr(request.state, "service_provider", None)
    if scoped_provider is None:
        raise RuntimeError("Scoped service provider not found in request state.")
    return scoped_provider.get_required_service(ChatService)


async def get_current_user(
    request: Request,
) -> dict:
    """
    Get current authenticated user from session.

    Args:
        request: FastAPI request

    Returns:
        User info dictionary

    Raises:
        HTTPException: 401 if not authenticated
    """
    # Extract session_id from cookie using configurable cookie name
    # This allows multiple apps on the same domain to have unique session cookies
    session_id = request.cookies.get(app_settings.session_cookie_name)

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
            headers={"WWW-Authenticate": "Cookie"},
        )

    auth_service = get_auth_service(request)

    # Try to refresh tokens if needed
    await auth_service.refresh_tokens(session_id)

    # Get user from session
    user = auth_service.get_user_from_session(session_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please log in again.",
            headers={"WWW-Authenticate": "Cookie"},
        )

    return user


async def get_access_token(
    request: Request,
) -> str:
    """
    Get the access token for the current session.

    Used for calling the Tools Provider API.

    Args:
        request: FastAPI request

    Returns:
        Access token string

    Raises:
        HTTPException: 401 if not authenticated or no token
    """
    # Extract session_id from cookie using configurable cookie name
    session_id = request.cookies.get(app_settings.session_cookie_name)

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    auth_service = get_auth_service(request)

    # Try to refresh tokens if needed
    await auth_service.refresh_tokens(session_id)

    token = auth_service.get_access_token(session_id)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No access token available",
        )

    return token


async def get_session_id(
    request: Request,
) -> Optional[str]:
    """
    Get the session ID from cookie (optional).

    Returns None if no session cookie present.
    """
    return request.cookies.get(app_settings.session_cookie_name)


async def require_session(
    request: Request,
) -> str:
    """
    Require a valid session ID.

    Args:
        request: FastAPI request

    Returns:
        Session ID

    Raises:
        HTTPException: 401 if no session
    """
    session_id = request.cookies.get(app_settings.session_cookie_name)
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session required",
        )
    return session_id


def has_role(user: dict, role: str) -> bool:
    """
    Check if a user has a specific role.

    Args:
        user: User info dictionary from authentication
        role: Role name to check for

    Returns:
        True if user has the role
    """
    # Check various claim locations for roles
    roles = user.get("roles", [])
    if not roles:
        roles = user.get("realm_access", {}).get("roles", [])
    if not roles:
        roles = user.get("resource_access", {}).get("account", {}).get("roles", [])

    return role in roles


async def require_admin(
    request: Request,
) -> dict:
    """
    Require the current user to have the 'admin' role.

    Args:
        request: FastAPI request

    Returns:
        User info dictionary

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin
    """
    user = await get_current_user(request)

    if not has_role(user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    return user
