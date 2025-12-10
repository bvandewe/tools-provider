"""Authentication service for Agent Host OAuth2 flow."""

import base64
import hashlib
import json
import logging
import secrets
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import FastAPI, Request, Response
from jwt import algorithms
from starlette.responses import Response as StarletteResponse

from application.settings import Settings
from infrastructure.session_store import RedisSessionStore

logger = logging.getLogger(__name__)


class AuthService:
    """
    Authentication service handling OAuth2 Authorization Code flow with Keycloak.

    Provides:
    - OAuth2 login/logout flows
    - Session management
    - Token validation and refresh
    """

    def __init__(
        self,
        session_store: RedisSessionStore,
        settings: Settings,
    ) -> None:
        """
        Initialize the auth service.

        Args:
            session_store: Redis session store
            settings: Application settings
        """
        self._session_store = session_store
        self._settings = settings
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_ttl_seconds: int = 3600
        # PKCE code verifiers stored by OAuth state parameter
        self._pending_code_verifiers: dict[str, str] = {}

    @staticmethod
    def configure_middleware(app: FastAPI) -> None:
        """Configure authentication middleware for the FastAPI application.

        This middleware:
        1. Creates a scoped service provider for each request (for scoped services like ChatService)
        2. Injects the AuthService instance into request state

        Args:
            app: The FastAPI application
        """
        from collections.abc import Awaitable

        @app.middleware("http")
        async def inject_services_middleware(
            request: Request,
            call_next: Callable[[Request], Awaitable[StarletteResponse]],
        ) -> StarletteResponse:
            """Middleware to inject services into FastAPI request state."""
            # Create a scoped service provider for this request
            # This allows scoped services (like ChatService) to be resolved
            async with app.state.services.create_async_scope() as scoped_provider:
                request.state.service_provider = scoped_provider
                # Retrieve auth service from root DI container (singleton)
                request.state.auth_service = app.state.services.get_required_service(AuthService)
                response = await call_next(request)
                return response

        logger.info("✅ AuthService middleware configured (with scoped service provider)")

    def get_authorization_url(self, state: str) -> str:
        """
        Get the Keycloak authorization URL for OAuth2 login with PKCE.

        Args:
            state: CSRF state parameter (also used as key to store code_verifier)

        Returns:
            Authorization URL to redirect the user to
        """
        # Generate PKCE code verifier and challenge
        code_verifier = self.generate_code_verifier()
        code_challenge = self._generate_code_challenge(code_verifier)

        # Store code_verifier keyed by state for retrieval during token exchange
        # Note: state may be "base_state:return_url", extract base state
        base_state = state.split(":")[0] if ":" in state else state
        self._pending_code_verifiers[base_state] = code_verifier

        params = {
            "client_id": self._settings.keycloak_client_id,
            "response_type": "code",
            "scope": "openid profile email roles",
            "redirect_uri": f"{self._settings.app_url}/api/auth/callback",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        base_url = f"{self._settings.keycloak_url}/realms/{self._settings.keycloak_realm}/protocol/openid-connect/auth"
        return f"{base_url}?{urlencode(params)}"

    @staticmethod
    def _generate_code_challenge(code_verifier: str) -> str:
        """Generate PKCE code challenge from code verifier using S256 method."""
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    @staticmethod
    def generate_code_verifier() -> str:
        """Generate a cryptographically random PKCE code verifier."""
        return secrets.token_urlsafe(64)

    async def exchange_code(self, code: str, state: str | None = None) -> dict[str, Any] | None:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from Keycloak callback
            state: OAuth state parameter to look up PKCE code_verifier

        Returns:
            Token response or None if exchange fails
        """
        # Retrieve PKCE code_verifier using state (extract base state if it has return_url appended)
        code_verifier = None
        if state:
            # State may be "base_state:return_url", extract just the base state
            base_state = state.split(":")[0] if ":" in state else state
            code_verifier = self._pending_code_verifiers.pop(base_state, None)
            if not code_verifier:
                logger.warning(f"No code_verifier found for state: {base_state}")

        token_url = f"{self._settings.keycloak_url_internal}/realms/{self._settings.keycloak_realm}/protocol/openid-connect/token"

        # Build token request data
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self._settings.keycloak_client_id,
            "redirect_uri": f"{self._settings.app_url}/api/auth/callback",
        }

        # Include code_verifier for PKCE
        if code_verifier:
            token_data["code_verifier"] = code_verifier

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    token_url,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                    return None

            except Exception as e:
                logger.error(f"Token exchange error: {e}")
                return None

    async def get_user_info(self, access_token: str) -> dict[str, Any] | None:
        """
        Get user info from Keycloak.

        Args:
            access_token: OAuth2 access token

        Returns:
            User info or None
        """
        userinfo_url = f"{self._settings.keycloak_url_internal}/realms/{self._settings.keycloak_realm}/protocol/openid-connect/userinfo"

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(
                    userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Userinfo request failed: {response.status_code}")
                    return None

            except Exception as e:
                logger.error(f"Userinfo error: {e}")
                return None

    def create_session(
        self,
        tokens: dict[str, Any],
        user_info: dict[str, Any],
    ) -> str:
        """
        Create a new session.

        Args:
            tokens: OAuth2 tokens
            user_info: User info from Keycloak

        Returns:
            Session ID
        """
        return self._session_store.create_session(tokens, user_info)

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session data."""
        return self._session_store.get_session(session_id)

    def get_user_from_session(self, session_id: str) -> dict[str, Any] | None:
        """Get user info from session."""
        session = self._session_store.get_session(session_id)
        if session:
            return session.get("user_info")
        return None

    def get_access_token(self, session_id: str) -> str | None:
        """Get access token from session."""
        return self._session_store.get_access_token(session_id)

    def delete_session(self, session_id: str) -> None:
        """Delete a session (logout)."""
        self._session_store.delete_session(session_id)

    async def refresh_tokens(self, session_id: str, force: bool = False) -> dict[str, Any]:
        """
        Refresh tokens if the access token is near expiry or if forced.

        Args:
            session_id: Session ID
            force: If True, always refresh regardless of token expiry

        Returns:
            Dict with:
            - status: "refreshed" | "valid" | "session_not_found" | "refresh_failed"
            - access_token_expires_in: seconds until access token expires (if available)
            - refresh_token_expires_in: seconds until refresh token expires (if available)
        """
        session = self._session_store.get_session(session_id)
        if not session:
            return {"status": "session_not_found"}

        tokens = session.get("tokens", {})
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        if not access_token or not refresh_token:
            return {"status": "session_not_found"}

        # Check if token is near expiry (unless forced)
        access_expires_in = None
        refresh_expires_in = None
        needs_refresh = force

        try:
            unverified = jwt.decode(access_token, options={"verify_signature": False})
            exp = unverified.get("exp")
            if isinstance(exp, int):
                access_expires_in = max(0, exp - int(time.time()))
                if not force and access_expires_in >= self._settings.refresh_auto_leeway_seconds:
                    # Token is still valid, no refresh needed
                    # Also get refresh token expiry for status response
                    try:
                        refresh_unverified = jwt.decode(refresh_token, options={"verify_signature": False})
                        refresh_exp = refresh_unverified.get("exp")
                        if isinstance(refresh_exp, int):
                            refresh_expires_in = max(0, refresh_exp - int(time.time()))
                    except Exception:
                        logger.debug("Failed to decode refresh_token for expiry check")

                    return {
                        "status": "valid",
                        "access_token_expires_in": access_expires_in,
                        "refresh_token_expires_in": refresh_expires_in,
                    }
                needs_refresh = True
        except Exception as e:
            logger.debug(f"Failed to decode access_token for expiry check: {e}")
            needs_refresh = True  # If we can't decode, try to refresh

        if not needs_refresh:
            return {
                "status": "valid",
                "access_token_expires_in": access_expires_in,
                "refresh_token_expires_in": refresh_expires_in,
            }

        # Perform refresh
        token_url = f"{self._settings.keycloak_url_internal}/realms/{self._settings.keycloak_realm}/protocol/openid-connect/token"

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": self._settings.keycloak_client_id,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    new_tokens = response.json()
                    self._session_store.update_tokens(session_id, new_tokens)
                    logger.info(f"Refreshed tokens for session {session_id[:8]}...")

                    # Get new token expiry times
                    new_access_expires_in = None
                    new_refresh_expires_in = None
                    try:
                        new_access = new_tokens.get("access_token")
                        if new_access:
                            unverified = jwt.decode(new_access, options={"verify_signature": False})
                            exp = unverified.get("exp")
                            if isinstance(exp, int):
                                new_access_expires_in = max(0, exp - int(time.time()))
                    except Exception:
                        logger.debug("Failed to decode new access_token for expiry check")

                    try:
                        new_refresh = new_tokens.get("refresh_token")
                        if new_refresh:
                            unverified = jwt.decode(new_refresh, options={"verify_signature": False})
                            exp = unverified.get("exp")
                            if isinstance(exp, int):
                                new_refresh_expires_in = max(0, exp - int(time.time()))
                    except Exception:
                        logger.debug("Failed to decode new refresh_token for expiry check")

                    return {
                        "status": "refreshed",
                        "access_token_expires_in": new_access_expires_in,
                        "refresh_token_expires_in": new_refresh_expires_in,
                    }
                else:
                    logger.warning(f"Token refresh failed: {response.status_code} - {response.text}")
                    return {"status": "refresh_failed", "error": f"Keycloak returned {response.status_code}"}

            except Exception as e:
                logger.error(f"Token refresh error: {e}")
                return {"status": "refresh_failed", "error": str(e)}

    def get_session_status(self, session_id: str) -> dict[str, Any] | None:
        """
        Get session status without triggering token refresh.

        Returns timing information about the session for frontend to
        determine if it should show warnings or refresh tokens.

        Args:
            session_id: Session ID

        Returns:
            Dict with session timing info or None if session not found
        """
        session = self._session_store.get_session(session_id)
        if not session:
            return None

        tokens = session.get("tokens", {})
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        result: dict[str, Any] = {
            "session_valid": True,
            "has_access_token": bool(access_token),
            "has_refresh_token": bool(refresh_token),
        }

        # Get access token expiry info
        if access_token:
            try:
                unverified = jwt.decode(access_token, options={"verify_signature": False})
                exp = unverified.get("exp")
                if isinstance(exp, int):
                    now = int(time.time())
                    result["access_token_expires_at"] = exp
                    result["access_token_expires_in"] = max(0, exp - now)
                    result["access_token_expired"] = now >= exp
            except Exception as e:
                logger.debug(f"Failed to decode access_token for status: {e}")
                result["access_token_expired"] = True

        # Get refresh token expiry info (if available - contains SSO session info)
        if refresh_token:
            try:
                unverified = jwt.decode(refresh_token, options={"verify_signature": False})
                exp = unverified.get("exp")
                if isinstance(exp, int):
                    now = int(time.time())
                    result["refresh_token_expires_at"] = exp
                    result["refresh_token_expires_in"] = max(0, exp - now)
                    result["refresh_token_expired"] = now >= exp
                # Session state (Keycloak-specific)
                if "session_state" in unverified:
                    result["session_state"] = unverified["session_state"]
            except Exception as e:
                logger.debug(f"Failed to decode refresh_token for status: {e}")

        # Include session metadata
        if "expires_at" in session:
            result["session_expires_at"] = session["expires_at"]

        return result

    def _fetch_jwks(self) -> dict[str, Any] | None:
        """Fetch JWKS from Keycloak for token validation."""
        now = time.time()
        if self._jwks_cache and (now - self._jwks_cache.get("fetched_at", 0) < self._jwks_ttl_seconds):
            return self._jwks_cache

        jwks_url = f"{self._settings.keycloak_url_internal}/realms/{self._settings.keycloak_realm}/protocol/openid-connect/certs"

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(jwks_url)
                response.raise_for_status()
                data = response.json()
                if "keys" in data:
                    self._jwks_cache = {"keys": data["keys"], "fetched_at": now}
                    return self._jwks_cache
        except Exception as e:
            logger.warning(f"JWKS fetch failed: {e}")

        return None

    def validate_access_token(self, access_token: str) -> dict[str, Any] | None:
        """
        Validate an access token and return claims.

        Args:
            access_token: JWT access token

        Returns:
            Token claims or None if invalid
        """
        try:
            # Get unverified header
            header = jwt.get_unverified_header(access_token)
            kid = header.get("kid")
            alg = header.get("alg")

            if alg != "RS256" or not kid:
                logger.warning(f"Unsupported token algorithm: {alg}")
                return None

            # Get public key from JWKS
            jwks = self._fetch_jwks()
            if not jwks:
                return None

            public_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    public_key = algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                    break

            if not public_key:
                logger.warning(f"Key {kid} not found in JWKS")
                return None

            # Verify token
            claims = jwt.decode(
                access_token,
                public_key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )

            return claims

        except jwt.ExpiredSignatureError:
            logger.info("Access token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return None

    @staticmethod
    def generate_state() -> str:
        """Generate a random state for CSRF protection."""
        return secrets.token_urlsafe(32)

    def set_session_cookie(
        self,
        response: Response,
        session_id: str,
    ) -> None:
        """Set session cookie in response.

        NOTE: Cookie name MUST be unique per application to avoid cross-app
        cookie collisions when multiple apps share the same domain (e.g., localhost).
        """
        response.set_cookie(
            key=self._settings.session_cookie_name,
            value=session_id,
            httponly=True,
            secure=self._settings.environment == "production",
            samesite="lax",
            max_age=self._settings.conversation_session_ttl_seconds,
        )

    def clear_session_cookie(self, response: Response) -> None:
        """Clear session cookie in response."""
        response.delete_cookie(key=self._settings.session_cookie_name)
