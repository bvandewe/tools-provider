"""FastAPI dependencies for authentication."""

import logging
from typing import Optional

from fastapi import Cookie, HTTPException, Request, status

from api.services.auth_service import AuthService
from application.services.chat_service import ChatService

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
    session_id: Optional[str] = Cookie(None),
) -> dict:
    """
    Get current authenticated user from session.

    Args:
        request: FastAPI request
        session_id: Session cookie value

    Returns:
        User info dictionary

    Raises:
        HTTPException: 401 if not authenticated
    """
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
    session_id: Optional[str] = Cookie(None),
) -> str:
    """
    Get the access token for the current session.

    Used for calling the Tools Provider API.

    Args:
        request: FastAPI request
        session_id: Session cookie value

    Returns:
        Access token string

    Raises:
        HTTPException: 401 if not authenticated or no token
    """
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
    session_id: Optional[str] = Cookie(None),
) -> Optional[str]:
    """
    Get the session ID from cookie (optional).

    Returns None if no session cookie present.
    """
    return session_id


async def require_session(
    session_id: Optional[str] = Cookie(None),
) -> str:
    """
    Require a valid session ID.

    Args:
        session_id: Session cookie value

    Returns:
        Session ID

    Raises:
        HTTPException: 401 if no session
    """
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session required",
        )
    return session_id
