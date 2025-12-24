"""Authentication API controller with OAuth2/OIDC flow with PKCE.

Provides endpoints for:
- OAuth2 login initiation (with PKCE)
- OAuth2 callback handling
- Session logout
- Current user information
"""

import base64
import hashlib
import logging
import secrets
from typing import Any
from urllib.parse import urlencode

import jwt
from classy_fastapi.decorators import get
from fastapi import Depends, Request, status
from fastapi.responses import RedirectResponse
from keycloak import KeycloakOpenID
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase

from api.dependencies import get_current_user
from application.settings import app_settings
from infrastructure.session_store import RedisSessionStore

log = logging.getLogger(__name__)


class AuthController(ControllerBase):
    """Controller for OAuth2/OIDC authentication with Keycloak.

    Flow:
    1. User clicks login → GET /api/auth/login → Redirect to Keycloak
    2. User enters credentials at Keycloak
    3. Keycloak redirects → GET /api/auth/callback?code=xxx
    4. Backend exchanges code for tokens
    5. Backend creates session, sets httpOnly cookie
    6. User accesses app with cookie automatically sent
    """

    def __init__(self, service_provider: ServiceProviderBase, mapper: Mapper, mediator: Mediator):
        super().__init__(service_provider, mapper, mediator)

        # Initialize Keycloak client with backend client
        self.keycloak = KeycloakOpenID(
            server_url=app_settings.keycloak_url_internal,
            client_id=app_settings.keycloak_client_id,
            realm_name=app_settings.keycloak_realm,
            client_secret_key=app_settings.keycloak_client_secret,
        )

        # Get session store from DI container
        session_store = service_provider.get_service(RedisSessionStore)
        if session_store is None:
            raise RuntimeError("RedisSessionStore not found in service provider")
        self.session_store: RedisSessionStore = session_store

    @get("/login")
    async def login(self, request: Request):
        """Initiate OAuth2 login with PKCE - redirect user to Keycloak login page.

        PKCE (Proof Key for Code Exchange) is required for public clients.
        We generate a code_verifier, hash it to create code_challenge,
        store the verifier in a temporary session, and send the challenge to Keycloak.

        Returns:
            Redirect to Keycloak authorization endpoint with PKCE parameters
        """
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(16)

        # Generate PKCE code_verifier and code_challenge
        # code_verifier: random 43-128 character string
        code_verifier = secrets.token_urlsafe(64)

        # code_challenge: base64url(sha256(code_verifier))
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")

        # Store state and code_verifier temporarily (using state as key)
        # This will be retrieved in the callback
        self.session_store.store_pkce(state, code_verifier)

        # Build base Keycloak authorization URL
        auth_url = self.keycloak.auth_url(
            redirect_uri=f"{app_settings.app_url}/api/auth/callback",
            scope="openid profile email roles",
            state=state,
        )

        # Add PKCE parameters to the URL
        pkce_params = urlencode(
            {
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
        auth_url = f"{auth_url}&{pkce_params}"

        # Replace internal URL with external URL for browser redirect
        if app_settings.keycloak_url_internal and app_settings.keycloak_url:
            auth_url = auth_url.replace(app_settings.keycloak_url_internal, app_settings.keycloak_url)
            auth_url = auth_url.replace("http://localhost:8080", app_settings.keycloak_url)

        return RedirectResponse(url=auth_url)

    @get("/callback")
    async def callback(
        self,
        code: str | None = None,
        state: str | None = None,
        error: str | None = None,
        error_description: str | None = None,
    ):
        """Handle OAuth2 callback from Keycloak with PKCE.

        Args:
            code: Authorization code from Keycloak (on success)
            state: CSRF protection token (on success) - also used to retrieve PKCE verifier
            error: Error code from Keycloak (on failure)
            error_description: Human-readable error description (on failure)

        Returns:
            Redirect to application home page with session cookie set (on success)
            Redirect to home page with error (on error)
        """
        # Handle OAuth2 error response from Keycloak
        if error:
            log.warning(f"OAuth2 callback error from Keycloak: {error} - {error_description}")
            # Redirect to home page (not login) to avoid redirect loop
            return RedirectResponse(url="/?error=auth_failed", status_code=status.HTTP_303_SEE_OTHER)

        if not code:
            log.warning("OAuth2 callback missing authorization code")
            return RedirectResponse(url="/?error=missing_code", status_code=status.HTTP_303_SEE_OTHER)

        if not state:
            log.warning("OAuth2 callback missing state parameter")
            return RedirectResponse(url="/?error=missing_state", status_code=status.HTTP_303_SEE_OTHER)

        # Retrieve the PKCE code_verifier using the state
        code_verifier = self.session_store.get_pkce(state)
        if not code_verifier:
            log.warning("OAuth2 callback - PKCE verifier not found for state")
            return RedirectResponse(url="/?error=invalid_state", status_code=status.HTTP_303_SEE_OTHER)

        try:
            # Exchange authorization code for tokens (with PKCE code_verifier)
            tokens = self.keycloak.token(
                grant_type="authorization_code",
                code=code,
                redirect_uri=f"{app_settings.app_url}/api/auth/callback",
                code_verifier=code_verifier,
            )

            # Get user information
            try:
                user_info: dict[str, Any] = self.keycloak.userinfo(tokens["access_token"])
            except Exception as e:
                log.warning(f"UserInfo endpoint failed: {e}. Falling back to token decoding.")
                user_info = jwt.decode(tokens["access_token"], options={"verify_signature": False})

            # Extract roles from access token
            try:
                access_token_decoded = jwt.decode(tokens["access_token"], options={"verify_signature": False})
                realm_roles = access_token_decoded.get("realm_access", {}).get("roles", [])
                if realm_roles:
                    user_roles = [role for role in realm_roles if role not in ["offline_access", "uma_authorization", "default-roles-tools-provider"]]
                    user_info["roles"] = user_roles
            except Exception as e:
                log.debug(f"Could not extract roles from access token: {e}")

            # Create server-side session
            session_id = self.session_store.create_session(tokens, user_info)

            # Create redirect response with session cookie
            redirect = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
            redirect.set_cookie(
                key=app_settings.session_cookie_name,
                value=session_id,
                httponly=True,
                secure=app_settings.environment == "production",
                samesite="lax",
                max_age=app_settings.session_timeout_hours * 60 * 60,
                path="/",
            )

            log.info(f"User {user_info.get('preferred_username', 'unknown')} logged in successfully")
            return redirect

        except Exception as e:
            log.error(f"OAuth2 callback error during token exchange: {e}")
            # Redirect to home page (not login) to avoid redirect loop
            return RedirectResponse(url="/?error=token_exchange_failed", status_code=status.HTTP_303_SEE_OTHER)

    @get("/logout")
    async def logout(self, request: Request):
        """Logout user by clearing session and cookie.

        Returns:
            Redirect to home page
        """
        session_id = request.cookies.get(app_settings.session_cookie_name)

        if session_id:
            # Delete session from Redis
            session = self.session_store.get_session(session_id)
            if session:
                # Try to logout from Keycloak
                try:
                    refresh_token = session.get("tokens", {}).get("refresh_token")
                    if refresh_token:
                        self.keycloak.logout(refresh_token)
                except Exception as e:
                    log.debug(f"Keycloak logout failed (non-critical): {e}")

                self.session_store.delete_session(session_id)
                log.info(f"User {session.get('user_info', {}).get('preferred_username', 'unknown')} logged out")

        # Clear session cookie
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(key=app_settings.session_cookie_name, path="/")

        return response

    @get("/me")
    async def me(self, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        """Get current authenticated user information.

        Returns:
            User information dictionary
        """
        return user
