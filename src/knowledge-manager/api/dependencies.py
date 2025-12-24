"""API dependency injection.

Provides authentication dependencies for knowledge-manager endpoints.
Supports dual authentication:
1. Session cookies (OAuth2 flow via Keycloak)
2. JWT Bearer tokens (for programmatic API access)

The HTTPBearer security scheme is exposed to OpenAPI so that SwaggerUI
shows the lock icon and allows authentication via the Authorize button.
"""

import logging
import time
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from neuroglia.mapping import Mapper
from neuroglia.mediation.mediator import Mediator

from api.services.auth_service import DualAuthService
from application.settings import Settings

log = logging.getLogger(__name__)

# Optional bearer token security scheme for OpenAPI documentation
# auto_error=False means it won't raise if no token provided (we handle dual auth)
security_optional = HTTPBearer(auto_error=False, scheme_name="oauth2")


@lru_cache
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()


def get_mongo_client(settings: Annotated[Settings, Depends(get_settings)]) -> AsyncIOMotorClient:
    """Get MongoDB client.

    Args:
        settings: Application settings

    Returns:
        Motor async MongoDB client
    """
    connection_strings = settings.get_connection_strings()
    mongodb_url = connection_strings.get("mongodb", "mongodb://localhost:27017")
    return AsyncIOMotorClient(mongodb_url)


def get_database(
    client: Annotated[AsyncIOMotorClient, Depends(get_mongo_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncIOMotorDatabase:
    """Get MongoDB database.

    Args:
        client: MongoDB client
        settings: Application settings

    Returns:
        Database instance
    """
    return client[settings.database_name]


async def get_mediator(request: Request) -> Mediator:
    """Get the mediator from DI container.

    Args:
        request: FastAPI request

    Returns:
        Mediator instance

    Raises:
        HTTPException: If mediator not found
    """
    # Try to get from services container first (neuroglia pattern)
    services = getattr(request.app.state, "services", None)
    if services is not None:
        mediator = services.get_service(Mediator)
        if mediator is not None:
            return mediator

    # Fallback to direct state (for compatibility)
    mediator = getattr(request.app.state, "mediator", None)
    if mediator is not None:
        return mediator

    log.error("Mediator not found in app state or services")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Service not properly initialized",
    )


async def get_mapper(request: Request) -> Mapper:
    """Get the mapper from DI container.

    Args:
        request: FastAPI request

    Returns:
        Mapper instance

    Raises:
        HTTPException: If mapper not found
    """
    # Try to get from services container first (neuroglia pattern)
    services = getattr(request.app.state, "services", None)
    if services is not None:
        mapper = services.get_service(Mapper)
        if mapper is not None:
            return mapper

    # Fallback to direct state (for compatibility)
    mapper = getattr(request.app.state, "mapper", None)
    if mapper is not None:
        return mapper

    log.error("Mapper not found in app state or services")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Service not properly initialized",
    )


async def get_auth_service(request: Request) -> DualAuthService:
    """Get the auth service from DI container.

    Args:
        request: FastAPI request

    Returns:
        DualAuthService instance

    Raises:
        HTTPException: If auth service not found
    """
    # Try to get from services container first (neuroglia pattern)
    services = getattr(request.app.state, "services", None)
    if services is not None:
        auth_service = services.get_service(DualAuthService)
        if auth_service is not None:
            return auth_service

    # Fallback to direct state (for compatibility)
    auth_service = getattr(request.app.state, "auth_service", None)
    if auth_service is not None:
        return auth_service

    log.error("Auth service not found in app state or services")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Service not properly initialized",
    )


async def get_current_user(
    request: Request,
    auth_service: Annotated[DualAuthService, Depends(get_auth_service)],
    credentials: HTTPAuthorizationCredentials | None = Security(security_optional),
) -> dict[str, Any]:
    """Get the current authenticated user from session or JWT Bearer token.

    Supports dual authentication:
    1. Session cookie (from OAuth2 login flow) - for browser/UI clients
    2. JWT Bearer token (Authorization header) - for API/programmatic access

    The Security(security_optional) parameter exposes this endpoint to OpenAPI
    as requiring authentication, enabling the lock icon in SwaggerUI.

    Args:
        request: FastAPI request
        auth_service: Authentication service
        credentials: Optional JWT Bearer token from Authorization header

    Returns:
        User information dictionary with claims and roles

    Raises:
        HTTPException: 401 if not authenticated via either method
    """
    settings = get_settings()

    # Extract session_id from cookie using configurable cookie name
    session_id = request.cookies.get(settings.session_cookie_name)

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

    # Try session-based authentication first (uses session_id internally)
    user = await auth_service.get_current_user(request)
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


def require_roles(*required_roles: str):
    """Dependency factory to require specific roles.

    Usage:
        @post("/")
        async def admin_endpoint(user: dict = Depends(require_roles("admin"))):
            ...

    Args:
        *required_roles: One or more role names required

    Returns:
        FastAPI dependency function that checks roles
    """

    async def role_checker(
        request: Request,
        auth_service: Annotated[DualAuthService, Depends(get_auth_service)],
        credentials: HTTPAuthorizationCredentials | None = Security(security_optional),
    ) -> dict[str, Any]:
        # Get authenticated user first
        user = await get_current_user(request, auth_service, credentials)

        # Extract roles from user
        user_roles = user.get("roles", [])

        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(required_roles)}",
            )
        return user

    return role_checker


async def get_optional_user(
    request: Request,
    auth_service: Annotated[DualAuthService, Depends(get_auth_service)],
) -> dict[str, Any] | None:
    """Get the current user if authenticated, None otherwise.

    Args:
        request: FastAPI request
        auth_service: Authentication service

    Returns:
        User information dictionary or None
    """
    return await auth_service.get_current_user(request)


# Type aliases for dependency injection
MediatorDep = Annotated[Mediator, Depends(get_mediator)]
MapperDep = Annotated[Mapper, Depends(get_mapper)]
CurrentUserDep = Annotated[dict[str, Any], Depends(get_current_user)]
OptionalUserDep = Annotated[dict[str, Any] | None, Depends(get_optional_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

# Admin user dependency - requires admin role
AdminUserDep = Annotated[dict[str, Any], Depends(require_roles("admin"))]
