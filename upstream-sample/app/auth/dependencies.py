"""
Authentication Dependencies - Keycloak JWT Validation & RBAC

Provides FastAPI dependencies for:
- JWT Bearer token validation using Keycloak JWKS
- Role-based access control (RBAC) enforcement
- OAuth2 Authorization Code flow for Swagger UI
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2AuthorizationCodeBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# Security schemes
# auto_error=False allows both schemes to be optional, we handle auth manually
bearer_scheme = HTTPBearer(auto_error=False)


def get_keycloak_url() -> str:
    """Get Keycloak URL based on environment."""
    # Use internal URL when running in Docker, external URL otherwise
    internal_url = os.getenv("KEYCLOAK_URL_INTERNAL", "")
    external_url = os.getenv("KEYCLOAK_URL", "http://localhost:8041")

    # Prefer internal URL if set (Docker environment)
    return internal_url if internal_url else external_url


def get_keycloak_external_url() -> str:
    """Get Keycloak external URL for OAuth2 flows (browser-facing)."""
    return os.getenv("KEYCLOAK_URL", "http://localhost:8041")


def get_keycloak_realm() -> str:
    """Get Keycloak realm name."""
    return os.getenv("KEYCLOAK_REALM", "tools-provider")


def create_oauth2_scheme() -> OAuth2AuthorizationCodeBearer:
    """Create OAuth2 Authorization Code Bearer scheme for Swagger UI."""
    keycloak_url = get_keycloak_external_url()
    realm = get_keycloak_realm()

    return OAuth2AuthorizationCodeBearer(
        authorizationUrl=f"{keycloak_url}/realms/{realm}/protocol/openid-connect/auth",
        tokenUrl=f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token",
        scopes={
            "openid": "OpenID Connect scope",
            "profile": "User profile information",
            "email": "User email address",
        },
        auto_error=False,  # Don't auto-error; we'll handle it manually to support both schemes
    )


# OAuth2 scheme instance for Swagger UI
oauth2_scheme = create_oauth2_scheme()

# JWKS cache
_jwks_client: dict | None = None
_jwks_keys: list[dict] = []


async def init_jwks_client() -> None:
    """Initialize JWKS client by fetching keys from Keycloak."""
    global _jwks_keys

    keycloak_url = get_keycloak_url()
    realm = get_keycloak_realm()
    jwks_url = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/certs"

    logger.info(f"Fetching JWKS from: {jwks_url}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            jwks_data = response.json()
            _jwks_keys = jwks_data.get("keys", [])
            logger.info(f"Loaded {len(_jwks_keys)} JWKS keys")
    except Exception as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        # Don't fail startup - keys will be fetched on first request
        _jwks_keys = []


async def get_jwks_keys() -> list[dict]:
    """Get JWKS keys, fetching if not cached."""
    if not _jwks_keys:
        await init_jwks_client()

    return _jwks_keys


def get_signing_key(token: str, keys: list[dict]) -> dict | None:
    """Find the signing key for a token from JWKS keys."""
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        for key in keys:
            if key.get("kid") == kid:
                return key

        logger.warning(f"No matching key found for kid: {kid}")
        return None
    except JWTError as e:
        logger.error(f"Error parsing token header: {e}")
        return None


@dataclass
class UserInfo:
    """User information extracted from JWT token."""

    sub: str
    username: str
    email: str | None = None
    name: str | None = None
    roles: list[str] = field(default_factory=list)
    raw_token: str = ""

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_any_role(self, roles: list[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)

    def has_all_roles(self, roles: list[str]) -> bool:
        """Check if user has all of the specified roles."""
        return all(role in self.roles for role in roles)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    oauth2_token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> UserInfo:
    """
    Validate JWT Bearer token and extract user information.

    This dependency validates the token against Keycloak's JWKS and extracts
    user claims including roles. Supports both:
    - HTTPBearer: For programmatic API access
    - OAuth2AuthorizationCode: For Swagger UI authentication
    """
    # Get token from either source
    token = None
    if oauth2_token:
        token = oauth2_token
    elif credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    keys = await get_jwks_keys()

    if not keys:
        logger.error("No JWKS keys available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )

    signing_key = get_signing_key(token, keys)
    if not signing_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Decode and validate the token
        keycloak_url = get_keycloak_url()
        realm = get_keycloak_realm()
        issuer = f"{keycloak_url}/realms/{realm}"

        # For local development, also accept localhost issuer variations
        external_url = os.getenv("KEYCLOAK_URL", "http://localhost:8041")
        valid_issuers = [
            issuer,
            f"{external_url}/realms/{realm}",
            f"http://keycloak:8080/realms/{realm}",
            f"http://localhost:8041/realms/{realm}",
        ]

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={
                "verify_aud": False,  # Allow any audience for demo
                "verify_iss": False,  # We'll verify manually due to Docker networking
            },
        )

        # Verify issuer manually (allowing multiple valid issuers)
        token_issuer = payload.get("iss", "")
        if not any(token_issuer == valid_iss for valid_iss in valid_issuers):
            logger.warning(f"Invalid issuer: {token_issuer}, expected one of: {valid_issuers}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract roles from the token
        # Keycloak can put roles in different places depending on configuration
        roles: list[str] = []

        # Check realm_access.roles (realm roles)
        realm_access = payload.get("realm_access", {})
        roles.extend(realm_access.get("roles", []))

        # Check direct roles claim (if configured with protocol mapper)
        if "roles" in payload:
            direct_roles = payload.get("roles", [])
            if isinstance(direct_roles, list):
                roles.extend(direct_roles)

        # Deduplicate roles
        roles = list(set(roles))

        return UserInfo(
            sub=payload.get("sub", ""),
            username=payload.get("preferred_username", payload.get("sub", "")),
            email=payload.get("email"),
            name=payload.get("name"),
            roles=roles,
            raw_token=token,
        )

    except JWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


class RoleChecker:
    """
    Dependency class for role-based access control.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: UserInfo = Depends(RoleChecker(["admin"]))):
            ...
    """

    def __init__(self, required_roles: list[str], require_all: bool = False):
        """
        Initialize role checker.

        Args:
            required_roles: List of roles that grant access
            require_all: If True, user must have ALL roles. If False, ANY role suffices.
        """
        self.required_roles = required_roles
        self.require_all = require_all

    async def __call__(
        self,
        user: Annotated[UserInfo, Depends(get_current_user)],
    ) -> UserInfo:
        """Check if user has required roles."""
        if self.require_all:
            has_access = user.has_all_roles(self.required_roles)
        else:
            has_access = user.has_any_role(self.required_roles)

        if not has_access:
            logger.warning(f"Access denied for user '{user.username}' with roles {user.roles}. " f"Required: {self.required_roles} (require_all={self.require_all})")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {self.required_roles}",
            )

        return user


def require_roles(roles: list[str], require_all: bool = False) -> RoleChecker:
    """
    Factory function for creating role checker dependencies.

    Args:
        roles: List of roles that grant access
        require_all: If True, user must have ALL roles. If False, ANY role suffices.

    Returns:
        RoleChecker dependency instance

    Usage:
        @router.get("/managers")
        async def manager_endpoint(user: UserInfo = Depends(require_roles(["manager", "admin"]))):
            ...
    """
    return RoleChecker(roles, require_all)


# Pre-configured role checkers for common patterns
# These map Keycloak realm roles to pizzeria business roles:
# - user -> Customer
# - developer -> Chef
# - manager -> Manager
# - admin -> Admin (full access)

CustomerOnly = RoleChecker(["user", "admin"])
ChefOnly = RoleChecker(["developer", "admin"])
ManagerOnly = RoleChecker(["manager", "admin"])
ChefOrManager = RoleChecker(["developer", "manager", "admin"])
AnyAuthenticated = RoleChecker(["user", "developer", "manager", "admin", "architect", "vendor"])
