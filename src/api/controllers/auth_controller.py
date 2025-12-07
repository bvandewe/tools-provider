"""Authentication API controller with OAuth2/OIDC flow."""

import logging
import secrets
from datetime import datetime
from urllib.parse import urlencode

import jwt
from classy_fastapi.decorators import get, post
from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse
from keycloak import KeycloakOpenID
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.mapping import Mapper
from neuroglia.mediation import Mediator
from neuroglia.mvc import ControllerBase

from application.settings import app_settings
from domain.events import UserLoggedInDomainEvent
from infrastructure import SessionStore

logger = logging.getLogger(__name__)


class AuthController(ControllerBase):
    """Portable Controller for OAuth2/OIDC authentication with Keycloak.

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

        # Initialize Keycloak client with CONFIDENTIAL backend client
        # This client has client_secret for secure token exchange
        self.keycloak = KeycloakOpenID(
            server_url=app_settings.keycloak_url_internal,
            client_id=app_settings.keycloak_client_id,
            realm_name=app_settings.keycloak_realm,
            client_secret_key=app_settings.keycloak_client_secret,
        )

        # Get session store from DI container as Controllers cant define additional dependencies
        session_store = service_provider.get_service(SessionStore)
        if session_store is None:
            raise RuntimeError("SessionStore not found in service provider")
        self.session_store: SessionStore = session_store

    @get("/login")
    async def login(self):
        """Initiate OAuth2 login - redirect user to Keycloak login page.

        Returns:
            Redirect to Keycloak authorization endpoint
        """
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(16)

        # Build Keycloak authorization URL
        # Note: Request roles scope to include user roles in token/userinfo
        # Use external URL for browser redirection
        auth_url = self.keycloak.auth_url(
            redirect_uri=f"{app_settings.app_url}/api/auth/callback",
            scope="openid profile email roles",
            state=state,
        )

        # Replace internal URL with external URL for the browser redirect
        if app_settings.keycloak_url_internal and app_settings.keycloak_url:
            auth_url = auth_url.replace(app_settings.keycloak_url_internal, app_settings.keycloak_url)
            # Also try replacing localhost:8080 if it appears (Keycloak 26 default hostname behavior)
            auth_url = auth_url.replace("http://localhost:8080", app_settings.keycloak_url)

        return RedirectResponse(url=auth_url)

    @get("/callback")
    async def callback(self, code: str, state: str):
        """Handle OAuth2 callback from Keycloak.

        Args:
            code: Authorization code from Keycloak
            state: CSRF protection token

        Returns:
            Redirect to application home page with session cookie set
        """
        try:
            # Exchange authorization code for tokens
            tokens = self.keycloak.token(
                grant_type="authorization_code",
                code=code,
                redirect_uri=f"{app_settings.app_url}/api/auth/callback",
            )

            # Get user information using access token
            # Note: We skip userinfo call if it fails due to issuer mismatch in dev environment
            # and rely on token decoding instead
            try:
                user_info = self.keycloak.userinfo(tokens["access_token"])
            except Exception as e:
                print(f"WARNING: UserInfo endpoint failed: {e}. Falling back to token decoding.")
                user_info = jwt.decode(tokens["access_token"], options={"verify_signature": False})

            # Extract roles from access token
            # Note: Keycloak includes roles in access token's realm_access claim,
            # but userinfo endpoint may not return them by default
            try:
                # Decode access token to extract realm roles (already validated by Keycloak)
                access_token_decoded = jwt.decode(tokens["access_token"], options={"verify_signature": False})

                # Get realm roles from token
                realm_roles = access_token_decoded.get("realm_access", {}).get("roles", [])

                # Add roles to user_info if present in token
                if realm_roles:
                    # Filter out default Keycloak roles (offline_access, uma_authorization)
                    user_roles = [
                        role
                        for role in realm_roles
                        if role
                        not in [
                            "offline_access",
                            "uma_authorization",
                            "default-roles-starter-app",
                        ]
                    ]
                    user_info["roles"] = user_roles

            except Exception as e:
                # Log error but continue - roles are optional for basic authentication
                print(f"Warning: Could not extract roles from access token: {e}")

            # Create server-side session
            session_id = self.session_store.create_session(tokens, user_info)
            aggregate_id = str(user_info.get("sub") or user_info.get("user_id") or user_info.get("preferred_username") or session_id)
            if self.mediator:
                await self.mediator.publish_async(
                    UserLoggedInDomainEvent(
                        aggregate_id=aggregate_id,
                        username=user_info.get("preferred_username") or "unknown",
                        login_at=datetime.now(),
                    )
                )
            # Create redirect response
            redirect = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

            # Set httpOnly cookie on the redirect response
            # NOTE: Cookie name MUST be unique per application to avoid cross-app collisions
            # when multiple apps share the same domain (e.g., localhost)
            redirect.set_cookie(
                key=app_settings.session_cookie_name,
                value=session_id,
                httponly=True,
                secure=app_settings.environment == "production",
                samesite="lax",
                max_age=app_settings.session_timeout_hours * 60 * 60,  # Convert hours to seconds
                path="/",
            )

            return redirect

        except Exception as e:
            # Log error and redirect to login
            print(f"OAuth2 callback error: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")

    @post("/refresh")
    async def refresh(self, request: Request):
        """Refresh session tokens using Keycloak refresh token.

        Returns new access/id tokens and updates the session store.
        """
        # Extract session_id from cookie using configurable cookie name
        session_id = request.cookies.get(app_settings.session_cookie_name)
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing session cookie",
            )
        session = self.session_store.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session",
            )
        session_tokens = session.get("tokens", {})
        refresh_token = session_tokens.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No refresh token available",
            )
        try:
            new_tokens = self.keycloak.refresh_token(refresh_token)
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Refresh failed: {e}")

        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = refresh_token
        if "id_token" not in new_tokens and session_tokens.get("id_token"):
            new_tokens["id_token"] = session_tokens.get("id_token")
        self.session_store.refresh_session(session_id, new_tokens)
        return {
            "access_token": new_tokens.get("access_token"),
            "id_token": new_tokens.get("id_token"),
        }

    @get("/logout")
    async def logout(self, request: Request):
        """Logout user - clear session and redirect to Keycloak logout.

        Args:
            request: FastAPI Request object

        Returns:
            Redirect to Keycloak logout endpoint
        """
        # Extract session_id from cookie using configurable cookie name
        session_id = request.cookies.get(app_settings.session_cookie_name)
        id_token = None
        refresh_token = None

        # Get id_token from session if available
        if session_id:
            session = self.session_store.get_session(session_id)
            if session:
                tokens = session.get("tokens", {})
                id_token = tokens.get("id_token")
                refresh_token = tokens.get("refresh_token")
            # Delete server-side session
            self.session_store.delete_session(session_id)

        params = {
            "post_logout_redirect_uri": f"{app_settings.app_url}/",
            "client_id": app_settings.keycloak_client_id,
        }
        if id_token:
            params["id_token_hint"] = id_token
        elif refresh_token:
            params["refresh_token"] = refresh_token

        # Build Keycloak logout URL with encoded parameters
        logout_url = f"{app_settings.keycloak_url}/realms/{app_settings.keycloak_realm}" f"/protocol/openid-connect/logout?{urlencode(params)}"

        # Create redirect and clear cookie using configurable cookie name
        redirect = RedirectResponse(url=logout_url, status_code=status.HTTP_303_SEE_OTHER)
        redirect.delete_cookie(app_settings.session_cookie_name, path="/")

        return redirect

    @get("/me")
    async def get_me(self, request: Request):
        """Get current authenticated user information.

        Alias for /user endpoint, provided for consistency with agent-host.

        Args:
            request: FastAPI Request object

        Returns:
            User information from Keycloak

        Raises:
            HTTPException: 401 if not authenticated or session expired
        """
        return await self.get_current_user(request)

    @get("/user")
    async def get_current_user(self, request: Request):
        """Get current authenticated user information.

        Args:
            request: FastAPI Request object

        Returns:
            User information from Keycloak

        Raises:
            HTTPException: 401 if not authenticated or session expired
        """
        # Extract session_id from cookie using configurable cookie name
        session_id = request.cookies.get(app_settings.session_cookie_name)
        if not session_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        # Retrieve session
        session = self.session_store.get_session(session_id)

        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

        # Return user info (never expose tokens to browser)
        return session["user_info"]

    @get("/session-settings")
    async def get_session_settings(self):
        """Get session configuration for the frontend.

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
        import httpx

        # Default fallback values if Keycloak is unreachable
        sso_session_idle_timeout = 1800  # 30 minutes default

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
            else:
                check_session_iframe = None

        except Exception as e:
            print(f"Warning: Failed to fetch OIDC config: {e}")
            check_session_iframe = None

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
