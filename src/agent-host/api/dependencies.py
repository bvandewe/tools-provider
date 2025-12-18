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
from fastapi import Depends, HTTPException, Query, Request, Security, WebSocket, WebSocketException, status
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


def require_roles(*required_roles: str):
    """Dependency factory to require specific roles.

    Creates a FastAPI dependency that checks if the authenticated user
    has at least one of the required roles. Uses the same role extraction
    logic as has_role().

    Usage:
        @get("/admin")
        async def admin_endpoint(user: dict = Depends(require_roles("admin"))):
            ...

        @post("/manage")
        async def manage_endpoint(user: dict = Depends(require_roles("admin", "manager"))):
            ...

    Args:
        *required_roles: One or more role names. User must have at least one.

    Returns:
        FastAPI dependency function that checks roles and returns user dict
    """

    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        # Check various claim locations for roles (same as has_role)
        user_roles = user.get("roles", [])
        if not user_roles:
            user_roles = user.get("realm_access", {}).get("roles", [])
        if not user_roles:
            user_roles = user.get("resource_access", {}).get("account", {}).get("roles", [])

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(required_roles)}",
            )
        return user

    return role_checker


def require_scopes(*required_scopes: str):
    """Dependency factory to require specific OAuth2 scopes.

    Creates a FastAPI dependency that checks if the authenticated user's
    token has at least one of the required scopes. Scopes are typically
    found in the 'scope' claim as a space-separated string.

    Usage:
        @get("/api/data")
        async def data_endpoint(user: dict = Depends(require_scopes("read:data"))):
            ...

        @post("/api/data")
        async def create_endpoint(user: dict = Depends(require_scopes("write:data", "admin:data"))):
            ...

    Args:
        *required_scopes: One or more scope names. User must have at least one.

    Returns:
        FastAPI dependency function that checks scopes and returns user dict
    """

    async def scope_checker(user: dict = Depends(get_current_user)) -> dict:
        # Scopes are typically a space-separated string in the 'scope' claim
        scope_claim = user.get("scope", "")
        if isinstance(scope_claim, str):
            user_scopes = scope_claim.split() if scope_claim else []
        elif isinstance(scope_claim, list):
            user_scopes = scope_claim
        else:
            user_scopes = []

        if not any(scope in user_scopes for scope in required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of scopes: {', '.join(required_scopes)}",
            )
        return user

    return scope_checker


def require_roles_and_scopes(roles: list[str], scopes: list[str]):
    """Dependency factory to require both specific roles AND scopes.

    Creates a FastAPI dependency that checks if the authenticated user
    has at least one of the required roles AND at least one of the required scopes.

    Usage:
        @get("/sensitive")
        async def sensitive_endpoint(
            user: dict = Depends(require_roles_and_scopes(["admin"], ["read:sensitive"]))
        ):
            ...

    Args:
        roles: List of role names. User must have at least one.
        scopes: List of scope names. User must have at least one.

    Returns:
        FastAPI dependency function that checks both and returns user dict
    """

    async def combined_checker(user: dict = Depends(get_current_user)) -> dict:
        # Check roles
        user_roles = user.get("roles", [])
        if not user_roles:
            user_roles = user.get("realm_access", {}).get("roles", [])
        if not user_roles:
            user_roles = user.get("resource_access", {}).get("account", {}).get("roles", [])

        if roles and not any(role in user_roles for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(roles)}",
            )

        # Check scopes
        scope_claim = user.get("scope", "")
        if isinstance(scope_claim, str):
            user_scopes = scope_claim.split() if scope_claim else []
        elif isinstance(scope_claim, list):
            user_scopes = scope_claim
        else:
            user_scopes = []

        if scopes and not any(scope in user_scopes for scope in scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of scopes: {', '.join(scopes)}",
            )

        return user

    return combined_checker


# =============================================================================
# WebSocket Authentication
# =============================================================================


async def get_ws_current_user(
    websocket: WebSocket,
    token: str | None = Query(None, description="JWT access token for WebSocket auth"),
) -> dict:
    """
    Get current authenticated user for WebSocket connections.

    Supports dual authentication:
    1. Session cookie (from browser) - same cookie used for HTTP requests
    2. JWT token via query parameter - for programmatic access

    Args:
        websocket: The WebSocket connection
        token: Optional JWT token from query parameter

    Returns:
        User info dictionary with claims and roles

    Raises:
        WebSocketException: If not authenticated
    """
    # Get auth service from app state (injected during startup)
    auth_service: AuthService | None = getattr(websocket.app.state, "auth_service", None)
    if auth_service is None:
        logger.error("AuthService not found in app state for WebSocket")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Auth service not configured")

    # Extract session_id from cookie
    session_id = websocket.cookies.get(app_settings.session_cookie_name)

    # Pre-check bearer token expiry
    if token:
        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
            exp = unverified.get("exp")
            if isinstance(exp, int) and exp < int(time.time()):
                raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Token expired")
        except WebSocketException:
            raise
        except (jwt.PyJWTError, ValueError, TypeError):
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token format")

    # Try session-based authentication first (browser with cookies)
    if session_id:
        await auth_service.refresh_tokens(session_id)
        user = auth_service.get_user_from_session(session_id)
        if user is not None:
            logger.debug(f"WebSocket authenticated via session: {user.get('sub', 'unknown')}")
            return user

    # Try JWT token authentication (from query param)
    if token:
        user = auth_service.validate_access_token(token)
        if user is not None:
            logger.debug(f"WebSocket authenticated via token: {user.get('sub', 'unknown')}")
            return user

    # Neither method worked
    if not session_id and not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Not authenticated. Provide session cookie or token query parameter.",
        )

    raise WebSocketException(
        code=status.WS_1008_POLICY_VIOLATION,
        reason="Session expired or invalid token.",
    )


async def get_ws_access_token(
    websocket: WebSocket,
    token: str | None = Query(None, description="JWT access token for WebSocket auth"),
) -> str:
    """
    Get the access token for WebSocket connections.

    Used for calling the Tools Provider API during WebSocket sessions.

    Args:
        websocket: The WebSocket connection
        token: Optional JWT token from query parameter

    Returns:
        Access token string

    Raises:
        WebSocketException: If no token available
    """
    # If token provided via query param, return it directly
    if token:
        return token

    # Get auth service from app state
    auth_service: AuthService | None = getattr(websocket.app.state, "auth_service", None)
    if auth_service is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Auth service not configured")

    # Extract session_id from cookie
    session_id = websocket.cookies.get(app_settings.session_cookie_name)

    if not session_id:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Not authenticated")

    # Try to refresh tokens if needed
    await auth_service.refresh_tokens(session_id)

    access_token = auth_service.get_access_token(session_id)
    if not access_token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="No access token available")

    return access_token


def get_ws_service_provider(websocket: WebSocket):
    """
    Get the service provider for WebSocket connections.

    Returns the root service provider which can be used to create scopes.

    Args:
        websocket: The WebSocket connection

    Returns:
        ServiceProvider instance
    """
    # Neuroglia uses 'services' on app.state
    service_provider = getattr(websocket.app.state, "services", None)
    if service_provider is None:
        raise WebSocketException(code=status.WS_1011_INTERNAL_ERROR, reason="Service provider not configured")
    return service_provider
