"""Authentication controller for OAuth2 login/logout flows."""

import logging
from datetime import datetime
from urllib.parse import urlencode

import httpx
from classy_fastapi.decorators import get, post
from fastapi import HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase

from api.services.auth_service import AuthService
from application.settings import app_settings
from domain.events.user import UserLoggedInDomainEvent, UserLoggedOutDomainEvent
from infrastructure.session_store import RedisSessionStore

logger = logging.getLogger(__name__)


class AuthController(ControllerBase):
    """Controller for OAuth2 authentication flows."""

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)
        self._auth_service: AuthService | None = None
        self._session_store: RedisSessionStore | None = None

    @property
    def auth_service(self) -> AuthService:
        """Lazy-load AuthService from DI container."""
        if self._auth_service is None:
            self._auth_service = self.service_provider.get_required_service(AuthService)
        return self._auth_service

    @property
    def session_store(self) -> RedisSessionStore:
        """Lazy-load RedisSessionStore from DI container."""
        if self._session_store is None:
            self._session_store = self.service_provider.get_required_service(RedisSessionStore)
        return self._session_store

    @get("/login")
    async def login(
        self,
        return_url: str | None = Query(None, description="URL to redirect after login"),
    ) -> RedirectResponse:
        """
        Initiate OAuth2 login flow.

        Redirects user to Keycloak for authentication.
        """
        state = self.auth_service.generate_state()

        # Store return URL in state (simple approach - could use Redis for complex state)
        if return_url:
            state = f"{state}:{return_url}"

        auth_url = self.auth_service.get_authorization_url(state)
        logger.info("Redirecting to Keycloak for login")

        return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)

    @get("/callback")
    async def callback(
        self,
        code: str | None = Query(None),
        state: str | None = Query(None),
        error: str | None = Query(None),
        error_description: str | None = Query(None),
    ) -> RedirectResponse:
        """
        OAuth2 callback handler.

        Exchanges authorization code for tokens and creates session.
        """
        # Handle OAuth errors
        if error:
            logger.error(f"OAuth error: {error} - {error_description}")
            return RedirectResponse(
                url=f"/?error={error}&error_description={error_description or ''}",
                status_code=status.HTTP_302_FOUND,
            )

        if not code:
            logger.error("No authorization code in callback")
            return RedirectResponse(
                url="/?error=no_code",
                status_code=status.HTTP_302_FOUND,
            )

        # Exchange code for tokens (pass state for PKCE code_verifier lookup)
        tokens = await self.auth_service.exchange_code(code, state)
        if not tokens:
            logger.error("Token exchange failed")
            return RedirectResponse(
                url="/?error=token_exchange_failed",
                status_code=status.HTTP_302_FOUND,
            )

        # Get user info
        access_token = tokens.get("access_token")
        user_info = await self.auth_service.get_user_info(access_token)

        if not user_info:
            # Try to extract from ID token
            id_token = tokens.get("id_token")
            if id_token:
                import jwt

                try:
                    user_info = jwt.decode(id_token, options={"verify_signature": False})
                except Exception as e:
                    logger.debug(f"Failed to decode id_token: {e}")

        if not user_info:
            user_info = {"sub": "unknown"}

        # Create session
        session_id = self.auth_service.create_session(tokens, user_info)
        username = user_info.get("preferred_username", "unknown")
        logger.info(f"Created session for user {username}")

        # Publish login event
        aggregate_id = str(user_info.get("sub") or user_info.get("user_id") or username or session_id)
        await self.mediator.publish_async(
            UserLoggedInDomainEvent(
                aggregate_id=aggregate_id,
                username=username,
                login_at=datetime.now(),
            )
        )

        # Determine redirect URL from state
        return_url = "/"
        if state and ":" in state:
            _, return_url = state.split(":", 1)

        # Create redirect response with session cookie
        response = RedirectResponse(url=return_url, status_code=status.HTTP_302_FOUND)
        self.auth_service.set_session_cookie(response, session_id)

        return response

    @get("/logout")
    async def logout(
        self,
        request: Request,
    ) -> RedirectResponse:
        """
        Logout user.

        Clears session and optionally redirects to Keycloak logout.
        """
        # Extract session_id from cookie using configurable cookie name
        session_id = request.cookies.get(app_settings.session_cookie_name)

        # Get tokens and user info before clearing session for Keycloak logout
        id_token_hint = None
        username = "unknown"
        aggregate_id = session_id or "unknown"

        if session_id:
            session = self.auth_service.get_session(session_id)
            if session:
                tokens = session.get("tokens", {})
                id_token_hint = tokens.get("id_token")
                user_info = session.get("user_info", {})
                username = user_info.get("preferred_username", "unknown")
                aggregate_id = str(user_info.get("sub") or user_info.get("user_id") or username or session_id)

            # Delete session
            self.auth_service.delete_session(session_id)

            # Publish logout event
            await self.mediator.publish_async(
                UserLoggedOutDomainEvent(
                    aggregate_id=aggregate_id,
                    username=username,
                    logout_at=datetime.now(),
                )
            )

        # Build Keycloak logout URL
        logout_url = f"{app_settings.keycloak_url}/realms/{app_settings.keycloak_realm}/protocol/openid-connect/logout"

        params = {
            "post_logout_redirect_uri": app_settings.app_url,
            "client_id": app_settings.keycloak_client_id,
        }

        if id_token_hint:
            params["id_token_hint"] = id_token_hint

        logout_redirect = f"{logout_url}?{urlencode(params)}"

        # Create response and clear cookie
        response = RedirectResponse(url=logout_redirect, status_code=status.HTTP_302_FOUND)
        self.auth_service.clear_session_cookie(response)

        logger.info("User logged out")
        return response

    @get("/me")
    async def get_current_user_info(
        self,
        request: Request,
    ) -> dict:
        """
        Get current user information.

        Returns user info from session if authenticated.
        """
        # Extract session_id from cookie using configurable cookie name
        session_id = request.cookies.get(app_settings.session_cookie_name)

        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        # Try to refresh tokens
        await self.auth_service.refresh_tokens(session_id)

        user = self.auth_service.get_user_from_session(session_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired",
            )

        # Extract roles from various claim locations
        roles = user.get("roles", [])
        if not roles:
            roles = user.get("realm_access", {}).get("roles", [])
        if not roles:
            roles = user.get("resource_access", {}).get("account", {}).get("roles", [])

        return {
            "authenticated": True,
            "user": {
                "id": user.get("sub"),
                "username": user.get("preferred_username"),
                "email": user.get("email"),
                "name": user.get("name") or user.get("given_name"),
                "roles": roles,  # Include roles for frontend admin checks
            },
        }

    @post("/refresh")
    async def refresh(
        self,
        request: Request,
    ) -> dict:
        """
        Refresh session tokens using Keycloak refresh token.

        Returns session status. Will only actually refresh if access token
        is near expiry or already expired.

        Returns 200 OK with status if session is valid (whether refreshed or not).
        Returns 401 only if session is truly expired or not found.
        """
        # Extract session_id from cookie using configurable cookie name
        session_id = request.cookies.get(app_settings.session_cookie_name)

        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing session cookie",
            )

        # Try to refresh tokens (will only refresh if needed)
        result = await self.auth_service.refresh_tokens(session_id)

        if result["status"] == "session_not_found":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session not found or expired",
            )

        if result["status"] == "refresh_failed":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token refresh failed: {result.get('error', 'unknown error')}",
            )

        # Session is valid (either refreshed or still valid)
        if result["status"] == "refreshed":
            logger.info(f"Session {session_id[:8]}... tokens refreshed successfully")
        else:
            logger.debug(f"Session {session_id[:8]}... tokens still valid, no refresh needed")

        return {
            "status": result["status"],
            "access_token_expires_in": result.get("access_token_expires_in"),
            "refresh_token_expires_in": result.get("refresh_token_expires_in"),
        }

    @get("/session-status")
    async def get_session_status(
        self,
        request: Request,
    ) -> dict:
        """
        Get current session status without triggering token refresh.

        This endpoint allows the frontend to passively check session health
        to determine if it needs to show warnings or initiate refresh.

        Returns token expiry times and session validity without modifying
        the session state.
        """
        session_id = request.cookies.get(app_settings.session_cookie_name)

        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        status_info = self.auth_service.get_session_status(session_id)
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session not found",
            )

        return status_info

    @get("/session-settings")
    async def get_session_settings(self) -> dict:
        """
        Get session configuration for the frontend.

        Fetches the SSO session idle timeout from Keycloak's OIDC well-known
        configuration and combines it with local warning settings.

        The frontend uses this to:
        - Track user activity and manage idle timeout
        - Show warning modal before session expires
        - Implement OIDC Session Management iframe

        Returns:
            Dict with keycloak_url, realm, client_id, sso_session_idle_timeout_seconds,
            and session_expiration_warning_minutes
        """
        # Default fallback values if Keycloak is unreachable
        sso_session_idle_timeout = 1800  # 30 minutes default
        check_session_iframe = None

        try:
            # Fetch OIDC well-known configuration from Keycloak
            # Try internal URL first (for Docker), fall back to external URL (for local dev)
            urls_to_try = [
                f"{app_settings.keycloak_url_internal}/realms/{app_settings.keycloak_realm}/.well-known/openid-configuration",
                f"{app_settings.keycloak_url}/realms/{app_settings.keycloak_realm}/.well-known/openid-configuration",
            ]

            oidc_config = None
            async with httpx.AsyncClient(timeout=5.0) as client:
                for url in urls_to_try:
                    try:
                        response = await client.get(url)
                        if response.status_code == 200:
                            oidc_config = response.json()
                            break
                    except Exception as e:
                        logger.debug(f"Failed to fetch OIDC config from {url}: {e}")
                        continue

            if oidc_config:
                # Store check_session_iframe URL for frontend
                check_session_iframe = oidc_config.get("check_session_iframe")

        except Exception as e:
            logger.warning(f"Failed to fetch OIDC config: {e}")

        # Fix: Replace internal Keycloak URLs with external URL for frontend access
        # Keycloak may return URLs with localhost:8080 or keycloak:8080 depending on config
        if check_session_iframe:
            # Replace Docker internal hostname (keycloak:8080)
            if app_settings.keycloak_url_internal:
                check_session_iframe = check_session_iframe.replace(app_settings.keycloak_url_internal, app_settings.keycloak_url)
            # Also replace localhost:8080 (Keycloak's default internal port)
            check_session_iframe = check_session_iframe.replace("http://localhost:8080", app_settings.keycloak_url)

        return {
            "keycloak_url": app_settings.keycloak_url,
            "realm": app_settings.keycloak_realm,
            "client_id": app_settings.keycloak_client_id,
            "sso_session_idle_timeout_seconds": sso_session_idle_timeout,
            "session_expiration_warning_minutes": app_settings.session_expiration_warning_minutes,
            "check_session_iframe": check_session_iframe,
        }
