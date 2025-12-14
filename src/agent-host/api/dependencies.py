"""FastAPI dependencies for authentication.

Provides authentication dependencies for agent-host endpoints.
Supports dual authentication:
1. Session cookies (OAuth2 flow via Keycloak)
2. JWT Bearer tokens (for programmatic API access)

The HTTPBearer security scheme is exposed to OpenAPI so that SwaggerUI
shows the lock icon and allows authentication via the Authorize button.
"""

import logging
import time

import jwt
from fastapi import HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.services.auth_service import AuthService
from application.services.chat_service import ChatService
from application.settings import app_settings

logger = logging.getLogger(__name__)

# Optional bearer token security scheme for OpenAPI documentation
# auto_error=False means it won't raise if no token provided (we handle dual auth)
security_optional = HTTPBearer(auto_error=False, scheme_name="oauth2")


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
    credentials: HTTPAuthorizationCredentials | None = Security(security_optional),
) -> dict:
    """
    Get current authenticated user from session or JWT Bearer token.

    Supports dual authentication:
    1. Session cookie (from OAuth2 login flow) - for browser/UI clients
    2. JWT Bearer token (Authorization header) - for API/programmatic access

    The Security(security_optional) parameter exposes this endpoint to OpenAPI
    as requiring authentication, enabling the lock icon in SwaggerUI.

    Args:
        request: FastAPI request
        credentials: Optional JWT Bearer token from Authorization header

    Returns:
        User info dictionary with claims and roles

    Raises:
        HTTPException: 401 if not authenticated via either method
    """
    auth_service = get_auth_service(request)

    # Extract session_id from cookie using configurable cookie name
    session_id = request.cookies.get(app_settings.session_cookie_name)

    # Extract token from credentials if present
    token = credentials.credentials if credentials else None

    # Pre-check bearer token expiry for clearer error feedback
    if token:
        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
            exp = unverified.get("exp")
            if isinstance(exp, int) and exp < int(time.time()):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Bearer token expired. Re-authorize to obtain a new access token.",
                    headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="The access token expired"'},
                )
        except HTTPException:
            raise
        except (jwt.PyJWTError, ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid bearer token format.",
                headers={"WWW-Authenticate": 'Bearer error="invalid_token", error_description="Malformed token"'},
            )

    # Try session-based authentication first
    if session_id:
        # Try to refresh tokens if needed
        await auth_service.refresh_tokens(session_id)
        user = auth_service.get_user_from_session(session_id)
        if user is not None:
            return user

    # Try JWT bearer token authentication
    if token:
        user = auth_service.validate_access_token(token)
        if user is not None:
            return user

    # Neither method worked
    if not session_id and not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in or provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session expired or invalid token. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_access_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(security_optional),
) -> str:
    """
    Get the access token for the current session or from Bearer token.

    Used for calling the Tools Provider API.

    Args:
        request: FastAPI request
        credentials: Optional JWT Bearer token from Authorization header

    Returns:
        Access token string

    Raises:
        HTTPException: 401 if not authenticated or no token
    """
    # If Bearer token provided, return it directly
    if credentials:
        return credentials.credentials

    # Extract session_id from cookie using configurable cookie name
    session_id = request.cookies.get(app_settings.session_cookie_name)

    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
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
) -> str | None:
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
    credentials: HTTPAuthorizationCredentials | None = Security(security_optional),
) -> dict:
    """
    Require the current user to have the 'admin' role.

    Args:
        request: FastAPI request
        credentials: Optional JWT Bearer token from Authorization header

    Returns:
        User info dictionary

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin
    """
    user = await get_current_user(request, credentials)

    if not has_role(user, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )

    return user
