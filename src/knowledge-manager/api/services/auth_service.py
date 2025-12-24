"""Dual authentication service supporting session cookies and JWT tokens."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from fastapi import FastAPI, Request
from jose import JWTError, jwt
from keycloak import KeycloakOpenID
from starlette.responses import Response as StarletteResponse

from application.settings import Settings
from infrastructure.session_store import RedisSessionStore

log = logging.getLogger(__name__)


class DualAuthService:
    """Authentication service supporting both session-based and JWT authentication.

    This service provides dual authentication for:
    1. Session-based: OAuth2/OIDC via Keycloak (for UI interactions)
    2. Bearer token: JWT validation (for API/service clients)
    """

    def __init__(
        self,
        settings: Settings,
        session_store: RedisSessionStore,
    ):
        self._settings = settings
        self._session_store = session_store

        # Use internal URL for backend-to-backend communication
        # Use external URL only for browser redirects
        internal_url = settings.keycloak_url_internal or settings.keycloak_url

        # Initialize Keycloak client with INTERNAL URL (for backend operations)
        self._keycloak = KeycloakOpenID(
            server_url=internal_url,
            client_id=settings.keycloak_client_id,
            realm_name=settings.keycloak_realm,
            client_secret_key=settings.keycloak_client_secret,
        )

        # Cache for JWKS
        self._jwks: dict[str, Any] | None = None
        self._public_key: str | None = None

    @staticmethod
    def configure_middleware(app: FastAPI) -> None:
        """Configure authentication middleware for the FastAPI application.

        This middleware:
        1. Creates a scoped service provider for each request
        2. Injects the DualAuthService instance into request state

        Args:
            app: The FastAPI application
        """

        @app.middleware("http")
        async def inject_services_middleware(
            request: Request,
            call_next: Callable[[Request], Awaitable[StarletteResponse]],
        ) -> StarletteResponse:
            """Middleware to inject services into FastAPI request state."""
            # Create a scoped service provider for this request
            async with app.state.services.create_async_scope() as scoped_provider:
                request.state.service_provider = scoped_provider
                # Retrieve auth service from root DI container (singleton)
                request.state.auth_service = app.state.services.get_required_service(DualAuthService)
                response = await call_next(request)
                return response

        log.info("✅ DualAuthService middleware configured")

    async def get_current_user(self, request: Request) -> dict[str, Any] | None:
        """Get the current user from session or JWT token.

        Checks in order:
        1. Session cookie (for OAuth2 BFF pattern)
        2. Authorization header (Bearer token)

        Args:
            request: FastAPI request

        Returns:
            User information dictionary or None if not authenticated
        """
        # Try session first
        user = await self._get_user_from_session(request)
        if user is not None:
            return user

        # Try JWT token
        user = await self._get_user_from_token(request)
        if user is not None:
            return user

        return None

    async def _get_user_from_session(self, request: Request) -> dict[str, Any] | None:
        """Get user from session cookie.

        Args:
            request: FastAPI request

        Returns:
            User info or None
        """
        # Use configurable cookie name from settings
        session_id = request.cookies.get(self._settings.session_cookie_name)
        if not session_id:
            return None

        session_data = await self._session_store.get(session_id)
        if session_data is None:
            return None

        # Extract user_info from session data
        user_info = session_data.get("user_info") or session_data.get("user")
        if not user_info:
            return None

        return user_info

    async def _get_user_from_token(self, request: Request) -> dict[str, Any] | None:
        """Get user from JWT bearer token.

        Args:
            request: FastAPI request

        Returns:
            User info or None
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:]  # Remove "Bearer " prefix

        try:
            # Get public key for token verification
            public_key = await self._get_public_key()
            if not public_key:
                log.error("Failed to get public key for JWT verification")
                return None

            # Determine audience validation settings
            verify_aud = self._settings.verify_audience and bool(self._settings.expected_audience)
            audience = self._settings.expected_audience if verify_aud else None

            # Decode and verify token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=audience,
                options={
                    "verify_exp": True,
                    "verify_aud": verify_aud,
                },
            )

            # Extract roles from realm_access (Keycloak standard)
            roles: list[str] = []
            if isinstance(payload.get("realm_access"), dict):
                roles = payload.get("realm_access", {}).get("roles", []) or []
            elif isinstance(payload.get("roles"), list):
                roles = list(payload.get("roles") or [])

            # Filter out Keycloak internal roles
            filtered_roles = [role for role in roles if role not in ["offline_access", "uma_authorization", "default-roles-tools-provider"]]

            # Extract user info from token
            user = {
                "sub": payload.get("sub"),
                "email": payload.get("email"),
                "preferred_username": payload.get("preferred_username"),
                "username": payload.get("preferred_username"),
                "name": payload.get("name"),
                "given_name": payload.get("given_name"),
                "family_name": payload.get("family_name"),
                "roles": filtered_roles,
                "realm_access": payload.get("realm_access", {}),
                "resource_access": payload.get("resource_access", {}),
            }

            return user

        except JWTError as e:
            log.warning(f"JWT verification failed: {e}")
            return None

    async def _get_public_key(self) -> str | None:
        """Get Keycloak public key for JWT verification.

        Returns:
            Public key string or None
        """
        if self._public_key:
            return self._public_key

        try:
            # Use internal URL for backend-to-backend communication
            internal_url = self._settings.keycloak_url_internal or self._settings.keycloak_url
            certs_url = f"{internal_url}/realms/{self._settings.keycloak_realm}/protocol/openid-connect/certs"

            async with httpx.AsyncClient() as client:
                response = await client.get(certs_url, timeout=10.0)
                response.raise_for_status()
                self._jwks = response.json()

            # Get the public key from Keycloak (simpler approach using keycloak library)
            self._public_key = self._keycloak.public_key()
            if self._public_key:
                # Format as PEM
                self._public_key = f"-----BEGIN PUBLIC KEY-----\n{self._public_key}\n-----END PUBLIC KEY-----"

            return self._public_key

        except Exception as e:
            log.error(f"Failed to get public key: {e}")
            return None

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Get Keycloak authorization URL for OAuth2 flow.

        Args:
            redirect_uri: Where to redirect after auth
            state: CSRF state parameter

        Returns:
            Authorization URL
        """
        return self._keycloak.auth_url(
            redirect_uri=redirect_uri,
            state=state,
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> dict[str, Any] | None:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code
            redirect_uri: Must match original redirect_uri

        Returns:
            Token response or None
        """
        try:
            token = self._keycloak.token(
                grant_type="authorization_code",
                code=code,
                redirect_uri=redirect_uri,
            )
            return token
        except Exception as e:
            log.error(f"Token exchange failed: {e}")
            return None

    async def get_user_info(self, access_token: str) -> dict[str, Any] | None:
        """Get user info from Keycloak.

        Args:
            access_token: Valid access token

        Returns:
            User info or None
        """
        try:
            return self._keycloak.userinfo(access_token)
        except Exception as e:
            log.error(f"Failed to get user info: {e}")
            return None

    async def refresh_token(self, refresh_token: str) -> dict[str, Any] | None:
        """Refresh access token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New token response or None
        """
        try:
            return self._keycloak.refresh_token(refresh_token)
        except Exception as e:
            log.error(f"Token refresh failed: {e}")
            return None

    async def logout(self, refresh_token: str) -> bool:
        """Logout user from Keycloak.

        Args:
            refresh_token: User's refresh token

        Returns:
            True if successful
        """
        try:
            self._keycloak.logout(refresh_token)
            return True
        except Exception as e:
            log.error(f"Logout failed: {e}")
            return False
