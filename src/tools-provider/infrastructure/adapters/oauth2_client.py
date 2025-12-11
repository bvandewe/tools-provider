"""OAuth2 Client Credentials Token Service.

Handles acquiring tokens using the OAuth2 client credentials grant for
service-to-service authentication (Level 2 auth mode).

This service supports two variants:
- Variant A: Use Tools Provider's own service account (default credentials)
- Variant B: Use source-specific credentials configured per upstream source

Key Features:
- Token caching with automatic refresh
- Configurable buffer before token expiry
- Support for both default and source-specific credentials
- Async-safe with locking
- Comprehensive logging

Usage:
    # Using default (Tools Provider) credentials
    token = await service.get_token()

    # Using source-specific credentials
    token = await service.get_token(
        token_url="https://auth.example.com/token",
        client_id="source-client",
        client_secret="source-secret",  # pragma: allowlist secret
        scopes=["read:data", "write:data"],
    )
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class ClientCredentialsToken:
    """Cached client credentials token.

    Attributes:
        access_token: The OAuth2 access token
        expires_at: Absolute expiry time (UTC)
        scope: Granted scopes (space-separated string)
        token_type: Token type (usually "Bearer")
    """

    access_token: str
    expires_at: datetime
    scope: str | None = None
    token_type: str = "Bearer"

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """Check if token is expired or will expire within buffer period.

        Args:
            buffer_seconds: Consider expired if within this many seconds of expiry

        Returns:
            True if token should be refreshed
        """
        threshold = datetime.now(UTC) + timedelta(seconds=buffer_seconds)
        return self.expires_at <= threshold


@dataclass
class ClientCredentialsError(Exception):
    """Error during client credentials token acquisition.

    Attributes:
        message: Human-readable error message
        error_code: OAuth2 error code (e.g., "invalid_client", "unauthorized_client")
        error_description: Detailed error description from auth server
        status_code: HTTP status code
    """

    message: str
    error_code: str | None = None
    error_description: str | None = None
    status_code: int | None = None

    def __str__(self) -> str:
        parts = [self.message]
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        if self.error_description:
            parts.append(f": {self.error_description}")
        return " ".join(parts)


class OAuth2ClientCredentialsService:
    """Service for acquiring OAuth2 client credentials tokens.

    Implements the OAuth2 client_credentials grant type for service-to-service
    authentication. Supports both:
    - Default credentials (Tools Provider's service account)
    - Source-specific credentials (per-source client ID/secret)

    Features:
    - Token caching with automatic refresh
    - Thread-safe async operations
    - Configurable expiry buffer

    Example:
        service = OAuth2ClientCredentialsService(
            default_token_url="https://keycloak.example.com/token",
            default_client_id="tools-provider-service",
            default_client_secret="secret",  # pragma: allowlist secret
        )

        # Use default credentials
        token = await service.get_token()

        # Use source-specific credentials
        token = await service.get_token(
            token_url="https://other-idp.example.com/token",
            client_id="custom-client",
            client_secret="custom-secret",  # pragma: allowlist secret
        )
    """

    def __init__(
        self,
        default_token_url: str,
        default_client_id: str,
        default_client_secret: str,
        http_timeout: float = 10.0,
        cache_buffer_seconds: int = 60,
    ) -> None:
        """Initialize the client credentials service.

        Args:
            default_token_url: OAuth2 token endpoint for default credentials
            default_client_id: Client ID for Tools Provider service account
            default_client_secret: Client secret for Tools Provider service account
            http_timeout: HTTP request timeout in seconds
            cache_buffer_seconds: Refresh token this many seconds before expiry
        """
        self._default_token_url = default_token_url
        self._default_client_id = default_client_id
        self._default_client_secret = default_client_secret
        self._http_timeout = http_timeout
        self._cache_buffer = cache_buffer_seconds

        # Token cache: keyed by (token_url, client_id)
        self._cache: dict[tuple[str, str], ClientCredentialsToken] = {}
        self._lock = asyncio.Lock()

        logger.info(
            "OAuth2ClientCredentialsService initialized",
            extra={
                "default_token_url": default_token_url,
                "default_client_id": default_client_id,
                "cache_buffer_seconds": cache_buffer_seconds,
            },
        )

    @property
    def is_configured(self) -> bool:
        """Check if the service has default credentials configured.

        Returns:
            True if default token_url, client_id, and client_secret are set
        """
        return bool(self._default_token_url and self._default_client_id and self._default_client_secret)

    async def get_token(
        self,
        token_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        scopes: list[str] | None = None,
    ) -> str:
        """Get a client credentials token.

        If no credentials are provided, uses the default (Tools Provider's service account).

        Args:
            token_url: OAuth2 token endpoint (default: configured default)
            client_id: Client ID (default: configured default)
            client_secret: Client secret (default: configured default)
            scopes: Scopes to request (default: none)

        Returns:
            Access token string

        Raises:
            ClientCredentialsError: If token acquisition fails
            ValueError: If no credentials available (neither provided nor default)
        """
        # Use defaults if not specified
        effective_url = token_url or self._default_token_url
        effective_client_id = client_id or self._default_client_id
        effective_client_secret = client_secret or self._default_client_secret

        # Validate we have credentials
        if not effective_url or not effective_client_id or not effective_client_secret:
            raise ValueError("No client credentials available. Either provide credentials or configure defaults.")

        cache_key = (effective_url, effective_client_id)

        with tracer.start_as_current_span("oauth2_client_credentials.get_token") as span:
            span.set_attribute("oauth2.client_id", effective_client_id)
            span.set_attribute("oauth2.is_default", token_url is None)

            async with self._lock:
                # Check cache
                cached = self._cache.get(cache_key)
                if cached and not cached.is_expired(self._cache_buffer):
                    logger.debug(
                        "Client credentials cache hit",
                        extra={
                            "client_id": effective_client_id,
                            "expires_at": cached.expires_at.isoformat(),
                        },
                    )
                    span.set_attribute("oauth2.cache_hit", True)
                    return cached.access_token

                span.set_attribute("oauth2.cache_hit", False)

                # Acquire new token
                logger.info(
                    "Acquiring client credentials token",
                    extra={
                        "client_id": effective_client_id,
                        "token_url": effective_url,
                        "scopes": scopes,
                    },
                )

                token = await self._acquire_token(
                    token_url=effective_url,
                    client_id=effective_client_id,
                    client_secret=effective_client_secret,
                    scopes=scopes,
                )

                # Cache it
                self._cache[cache_key] = token
                span.set_attribute("oauth2.expires_in", (token.expires_at - datetime.now(UTC)).total_seconds())

                return token.access_token

    async def _acquire_token(
        self,
        token_url: str,
        client_id: str,
        client_secret: str,
        scopes: list[str] | None = None,
    ) -> ClientCredentialsToken:
        """Acquire a new token from the OAuth2 server.

        Args:
            token_url: OAuth2 token endpoint
            client_id: Client ID
            client_secret: Client secret
            scopes: Scopes to request

        Returns:
            ClientCredentialsToken with the acquired token

        Raises:
            ClientCredentialsError: If token acquisition fails
        """
        data: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if scopes:
            data["scope"] = " ".join(scopes)

        with tracer.start_as_current_span("oauth2_client_credentials.acquire_token") as span:
            span.set_attribute("http.url", token_url)
            span.set_attribute("oauth2.client_id", client_id)

            try:
                async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                    response = await client.post(
                        token_url,
                        data=data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    )

                    span.set_attribute("http.status_code", response.status_code)

                    if response.status_code != 200:
                        error_data = response.json() if response.content else {}
                        error = ClientCredentialsError(
                            message=f"Client credentials token acquisition failed for {client_id}",
                            error_code=error_data.get("error"),
                            error_description=error_data.get("error_description"),
                            status_code=response.status_code,
                        )
                        logger.error(
                            "Client credentials token acquisition failed",
                            extra={
                                "client_id": client_id,
                                "status_code": response.status_code,
                                "error_code": error.error_code,
                                "error_description": error.error_description,
                            },
                        )
                        span.set_attribute("oauth2.error", str(error))
                        raise error

                    token_data = response.json()
                    expires_in = token_data.get("expires_in", 300)

                    token = ClientCredentialsToken(
                        access_token=token_data["access_token"],
                        expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
                        scope=token_data.get("scope"),
                        token_type=token_data.get("token_type", "Bearer"),
                    )

                    logger.info(
                        "Client credentials token acquired",
                        extra={
                            "client_id": client_id,
                            "expires_in": expires_in,
                            "scope": token.scope,
                        },
                    )

                    return token

            except httpx.TimeoutException as e:
                error = ClientCredentialsError(
                    message=f"Timeout acquiring client credentials token from {token_url}",
                    status_code=None,
                )
                logger.error(
                    "Client credentials token acquisition timed out",
                    extra={"client_id": client_id, "token_url": token_url},
                    exc_info=e,
                )
                raise error from e

            except httpx.RequestError as e:
                error = ClientCredentialsError(
                    message=f"Network error acquiring client credentials token: {e}",
                    status_code=None,
                )
                logger.error(
                    "Client credentials token acquisition network error",
                    extra={"client_id": client_id, "token_url": token_url},
                    exc_info=e,
                )
                raise error from e

    def clear_cache(self, client_id: str | None = None) -> None:
        """Clear cached tokens.

        Args:
            client_id: If provided, only clear tokens for this client.
                       If None, clear all cached tokens.
        """
        if client_id is None:
            self._cache.clear()
            logger.info("Cleared all client credentials cache")
        else:
            keys_to_remove = [key for key in self._cache if key[1] == client_id]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info(f"Cleared client credentials cache for {client_id}", extra={"keys_removed": len(keys_to_remove)})
