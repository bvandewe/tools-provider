"""External Identity Provider Token Provider.

Handles token acquisition from external identity providers (IDPs) for
upstream sources that are authenticated with a different Keycloak/OAuth2
server than the Tools Provider's local IDP.

Supports two authentication flows:
1. Client Credentials Grant: Service-to-service authentication
2. Token Exchange (RFC 8693): User identity delegation

Key Features:
- OIDC Discovery for automatic endpoint resolution
- Token caching with automatic refresh
- Support for both flows with external IDPs
- Async-safe with proper error handling
- Comprehensive observability (tracing, logging)

Usage:
    provider = ExternalIdpTokenProvider()

    # Client credentials with external IDP
    token = await provider.get_client_credentials_token(
        issuer_url="https://external-kc.example.com/realms/partner",
        client_id="partner-api-client",
        client_secret="secret",  # pragma: allowlist secret
        scopes=["read:data"],
    )

    # Token exchange with external IDP
    exchanged_token = await provider.exchange_token(
        issuer_url="https://external-kc.example.com/realms/partner",
        subject_token="user-token-from-local-kc",
        client_id="partner-api-client",
        client_secret="secret",  # pragma: allowlist secret
        audience="partner-backend",
    )
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from opentelemetry import trace

from .oidc_discovery import OIDCDiscoveryService

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass
class ExternalIdpToken:
    """Token acquired from an external IDP.

    Attributes:
        access_token: The OAuth2 access token
        token_type: Token type (usually "Bearer")
        expires_at: Absolute expiry time (UTC)
        expires_in: Original expires_in value in seconds
        scope: Granted scopes (space-separated string)
        issued_token_type: Type of issued token (for token exchange)
    """

    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime | None = None
    expires_in: int = 300
    scope: str | None = None
    issued_token_type: str | None = None

    def __post_init__(self) -> None:
        """Calculate absolute expiry time if not set."""
        if self.expires_at is None:
            self.expires_at = datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=self.expires_in)

    def is_expired(self, leeway_seconds: int = 60) -> bool:
        """Check if token is expired or about to expire.

        Args:
            leeway_seconds: Consider expired if within this many seconds of expiry

        Returns:
            True if token should be refreshed
        """
        if self.expires_at is None:
            return True
        threshold = datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=leeway_seconds)
        return bool(self.expires_at <= threshold)


@dataclass
class ExternalIdpError(Exception):
    """Error during external IDP token operation.

    Attributes:
        message: Human-readable error message
        error_code: OAuth2 error code (e.g., "invalid_grant", "invalid_target")
        error_description: Detailed error description from the IDP
        status_code: HTTP status code
        issuer_url: The external IDP issuer URL
        is_retryable: Whether the error might succeed on retry
    """

    message: str
    issuer_url: str
    error_code: str | None = None
    error_description: str | None = None
    status_code: int | None = None
    is_retryable: bool = False

    def __str__(self) -> str:
        parts = [self.message]
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        if self.error_description:
            parts.append(f": {self.error_description}")
        parts.append(f"(issuer: {self.issuer_url})")
        return " ".join(parts)


class ExternalIdpTokenProvider:
    """Token provider for external identity providers.

    Handles token acquisition from external IDPs that are different from
    the Tools Provider's local Keycloak. Uses OIDC Discovery to automatically
    resolve token endpoints.

    Supports:
    - OAuth2 Client Credentials Grant (service-to-service)
    - RFC 8693 Token Exchange (user identity delegation)

    Features:
    - Automatic endpoint discovery via OIDC
    - Token caching with configurable buffer
    - Async-safe operations
    - Comprehensive observability

    Example:
        provider = ExternalIdpTokenProvider()

        # Client credentials
        token = await provider.get_client_credentials_token(
            issuer_url="https://external-kc.example.com/realms/partner",
            client_id="my-client",
            client_secret="secret",  # pragma: allowlist secret
        )

        # Token exchange
        exchanged = await provider.exchange_token(
            issuer_url="https://external-kc.example.com/realms/partner",
            subject_token="user-token",
            client_id="my-client",
            client_secret="secret",  # pragma: allowlist secret
            audience="target-service",
        )
    """

    # Token type URNs per RFC 8693 (standard identifiers, not secrets)
    ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"  # nosec B105
    REFRESH_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:refresh_token"  # nosec B105

    def __init__(
        self,
        discovery_service: OIDCDiscoveryService | None = None,
        http_timeout: float = 10.0,
        cache_buffer_seconds: int = 60,
    ) -> None:
        """Initialize the external IDP token provider.

        Args:
            discovery_service: Optional shared OIDC discovery service (creates new if None)
            http_timeout: HTTP request timeout in seconds
            cache_buffer_seconds: Refresh tokens this many seconds before expiry
        """
        self._discovery = discovery_service or OIDCDiscoveryService(http_timeout=http_timeout)
        self._http_timeout = http_timeout
        self._cache_buffer = cache_buffer_seconds

        # Token cache: keyed by cache key (issuer + client_id + hash)
        self._client_credentials_cache: dict[str, ExternalIdpToken] = {}
        self._token_exchange_cache: dict[str, ExternalIdpToken] = {}
        self._lock = asyncio.Lock()

        logger.info(f"ExternalIdpTokenProvider initialized (cache buffer: {cache_buffer_seconds}s)")

    def _generate_cache_key(
        self,
        issuer_url: str,
        client_id: str,
        scopes: list[str] | None = None,
        subject_token: str | None = None,
        audience: str | None = None,
    ) -> str:
        """Generate a cache key for token lookup.

        For client credentials: hash of (issuer, client_id, scopes)
        For token exchange: hash of (issuer, client_id, subject_token_hash, audience)

        Args:
            issuer_url: External IDP issuer URL
            client_id: Client ID
            scopes: OAuth2 scopes (for client credentials)
            subject_token: Subject token (for token exchange)
            audience: Target audience (for token exchange)

        Returns:
            Cache key string
        """
        key_parts = [issuer_url.rstrip("/"), client_id]

        if scopes:
            key_parts.append(":".join(sorted(scopes)))

        if subject_token:
            # Hash the subject token for privacy and key size
            token_hash = hashlib.sha256(subject_token.encode()).hexdigest()[:16]
            key_parts.append(token_hash)

        if audience:
            key_parts.append(audience)

        return "|".join(key_parts)

    async def get_client_credentials_token(
        self,
        issuer_url: str,
        client_id: str,
        client_secret: str,
        scopes: list[str] | None = None,
        skip_cache: bool = False,
    ) -> ExternalIdpToken:
        """Get a client credentials token from an external IDP.

        Uses OIDC Discovery to find the token endpoint, then performs
        the OAuth2 client_credentials grant.

        Args:
            issuer_url: OIDC issuer URL of the external IDP
            client_id: Client ID at the external IDP
            client_secret: Client secret
            scopes: OAuth2 scopes to request
            skip_cache: If True, bypass cache and fetch fresh token

        Returns:
            ExternalIdpToken with the access token

        Raises:
            ExternalIdpError: If token acquisition fails
            OIDCDiscoveryError: If OIDC discovery fails
        """
        with tracer.start_as_current_span("external_idp.client_credentials") as span:
            span.set_attribute("external_idp.issuer_url", issuer_url)
            span.set_attribute("external_idp.client_id", client_id)
            span.set_attribute("external_idp.scopes", ",".join(scopes) if scopes else "")

            # Check cache first
            cache_key = self._generate_cache_key(issuer_url, client_id, scopes=scopes)
            if not skip_cache:
                async with self._lock:
                    cached = self._client_credentials_cache.get(cache_key)
                    if cached and not cached.is_expired(self._cache_buffer):
                        span.set_attribute("external_idp.cache_hit", True)
                        logger.debug(f"External IDP client credentials cache hit for {issuer_url}")
                        return cached

            span.set_attribute("external_idp.cache_hit", False)

            # Discover token endpoint
            discovery = await self._discovery.get_discovery_document(issuer_url)
            token_endpoint = discovery.token_endpoint
            span.set_attribute("external_idp.token_endpoint", token_endpoint)

            # Acquire token
            token = await self._do_client_credentials(
                token_endpoint=token_endpoint,
                client_id=client_id,
                client_secret=client_secret,
                scopes=scopes,
                issuer_url=issuer_url,
            )

            # Cache the token
            async with self._lock:
                self._client_credentials_cache[cache_key] = token

            span.set_attribute("external_idp.expires_in", token.expires_in)
            logger.info(f"External IDP client credentials token acquired from {issuer_url}")
            return token

    async def _do_client_credentials(
        self,
        token_endpoint: str,
        client_id: str,
        client_secret: str,
        scopes: list[str] | None,
        issuer_url: str,
    ) -> ExternalIdpToken:
        """Perform the client credentials grant.

        Args:
            token_endpoint: OAuth2 token endpoint
            client_id: Client ID
            client_secret: Client secret
            scopes: Scopes to request
            issuer_url: Issuer URL (for error context)

        Returns:
            ExternalIdpToken with the access token

        Raises:
            ExternalIdpError: If token acquisition fails
        """
        data: dict[str, str] = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if scopes:
            data["scope"] = " ".join(scopes)

        try:
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                response = await client.post(
                    token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    token_data = response.json()
                    return ExternalIdpToken(
                        access_token=token_data["access_token"],
                        token_type=token_data.get("token_type", "Bearer"),
                        expires_in=token_data.get("expires_in", 300),
                        scope=token_data.get("scope"),
                    )

                # Handle error
                error_data = {}
                try:
                    error_data = response.json()
                except Exception:
                    logger.info("Failed to parse error response as JSON", exc_info=True)

                is_retryable = response.status_code in (502, 503, 504)
                raise ExternalIdpError(
                    message=f"Client credentials grant failed at {issuer_url}",
                    issuer_url=issuer_url,
                    error_code=error_data.get("error"),
                    error_description=error_data.get("error_description"),
                    status_code=response.status_code,
                    is_retryable=is_retryable,
                )

        except httpx.TimeoutException:
            raise ExternalIdpError(
                message="Token request timed out",
                issuer_url=issuer_url,
                is_retryable=True,
            )
        except httpx.RequestError as e:
            raise ExternalIdpError(
                message=f"Token request failed: {e}",
                issuer_url=issuer_url,
                is_retryable=True,
            )

    async def exchange_token(
        self,
        issuer_url: str,
        subject_token: str,
        client_id: str,
        client_secret: str,
        audience: str | None = None,
        requested_scopes: list[str] | None = None,
        skip_cache: bool = False,
    ) -> ExternalIdpToken:
        """Exchange a token at an external IDP (RFC 8693).

        Performs token exchange at the external IDP, exchanging the subject token
        (typically from the local Keycloak) for a new token issued by the external IDP.

        Prerequisites:
        - External IDP must be configured to trust the local IDP's tokens
        - External IDP must have the local IDP's JWKS cached for token validation
        - Client must have token-exchange permission at the external IDP

        Args:
            issuer_url: OIDC issuer URL of the external IDP
            subject_token: The token to exchange (from local IDP)
            client_id: Client ID at the external IDP
            client_secret: Client secret
            audience: Target audience for the exchanged token
            requested_scopes: Scopes to request in the exchanged token
            skip_cache: If True, bypass cache and perform fresh exchange

        Returns:
            ExternalIdpToken with the exchanged access token

        Raises:
            ExternalIdpError: If token exchange fails
            OIDCDiscoveryError: If OIDC discovery fails
        """
        with tracer.start_as_current_span("external_idp.token_exchange") as span:
            span.set_attribute("external_idp.issuer_url", issuer_url)
            span.set_attribute("external_idp.client_id", client_id)
            span.set_attribute("external_idp.audience", audience or "")
            span.set_attribute("external_idp.skip_cache", skip_cache)

            # Check cache first
            cache_key = self._generate_cache_key(
                issuer_url,
                client_id,
                subject_token=subject_token,
                audience=audience,
            )
            if not skip_cache:
                async with self._lock:
                    cached = self._token_exchange_cache.get(cache_key)
                    if cached and not cached.is_expired(self._cache_buffer):
                        span.set_attribute("external_idp.cache_hit", True)
                        logger.debug(f"External IDP token exchange cache hit for {issuer_url}")
                        return cached

            span.set_attribute("external_idp.cache_hit", False)

            # Discover token endpoint and verify token exchange support
            discovery = await self._discovery.get_discovery_document(issuer_url)
            token_endpoint = discovery.token_endpoint
            span.set_attribute("external_idp.token_endpoint", token_endpoint)

            if not discovery.supports_token_exchange():
                logger.warning(f"External IDP may not support token exchange: {issuer_url}")
                span.add_event("token_exchange_not_advertised")

            # Perform token exchange
            token = await self._do_token_exchange(
                token_endpoint=token_endpoint,
                subject_token=subject_token,
                client_id=client_id,
                client_secret=client_secret,
                audience=audience,
                requested_scopes=requested_scopes,
                issuer_url=issuer_url,
            )

            # Cache the token
            async with self._lock:
                self._token_exchange_cache[cache_key] = token

            span.set_attribute("external_idp.expires_in", token.expires_in)
            logger.info(f"External IDP token exchange successful at {issuer_url}")
            return token

    async def _do_token_exchange(
        self,
        token_endpoint: str,
        subject_token: str,
        client_id: str,
        client_secret: str,
        audience: str | None,
        requested_scopes: list[str] | None,
        issuer_url: str,
    ) -> ExternalIdpToken:
        """Perform the RFC 8693 token exchange.

        Args:
            token_endpoint: OAuth2 token endpoint
            subject_token: Subject token to exchange
            client_id: Client ID
            client_secret: Client secret
            audience: Target audience
            requested_scopes: Scopes to request
            issuer_url: Issuer URL (for error context)

        Returns:
            ExternalIdpToken with the exchanged token

        Raises:
            ExternalIdpError: If token exchange fails
        """
        data: dict[str, str] = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "client_id": client_id,
            "client_secret": client_secret,
            "subject_token": subject_token,
            "subject_token_type": self.ACCESS_TOKEN_TYPE,
            "requested_token_type": self.ACCESS_TOKEN_TYPE,
        }

        if audience:
            data["audience"] = audience

        if requested_scopes:
            data["scope"] = " ".join(requested_scopes)

        try:
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                response = await client.post(
                    token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    token_data = response.json()
                    return ExternalIdpToken(
                        access_token=token_data["access_token"],
                        token_type=token_data.get("token_type", "Bearer"),
                        expires_in=token_data.get("expires_in", 300),
                        scope=token_data.get("scope"),
                        issued_token_type=token_data.get(
                            "issued_token_type",
                            self.ACCESS_TOKEN_TYPE,
                        ),
                    )

                # Handle error
                error_data = {}
                try:
                    error_data = response.json()
                except Exception:
                    logger.info("Failed to parse error response as JSON", exc_info=True)

                error_code = error_data.get("error", "unknown_error")
                is_retryable = response.status_code in (502, 503, 504) or error_code in (
                    "temporarily_unavailable",
                    "server_error",
                )

                logger.warning(f"External IDP token exchange failed: status={response.status_code}, error={error_code}, issuer={issuer_url}")

                raise ExternalIdpError(
                    message="Token exchange failed at external IDP",
                    issuer_url=issuer_url,
                    error_code=error_code,
                    error_description=error_data.get("error_description"),
                    status_code=response.status_code,
                    is_retryable=is_retryable,
                )

        except httpx.TimeoutException:
            raise ExternalIdpError(
                message="Token exchange request timed out",
                issuer_url=issuer_url,
                is_retryable=True,
            )
        except httpx.RequestError as e:
            raise ExternalIdpError(
                message=f"Token exchange request failed: {e}",
                issuer_url=issuer_url,
                is_retryable=True,
            )

    def clear_cache(self, issuer_url: str | None = None) -> None:
        """Clear cached tokens.

        Args:
            issuer_url: Specific issuer to clear, or None to clear all
        """
        if issuer_url:
            issuer_prefix = issuer_url.rstrip("/")
            keys_to_remove = [k for k in self._client_credentials_cache if k.startswith(issuer_prefix)]
            for key in keys_to_remove:
                del self._client_credentials_cache[key]

            keys_to_remove = [k for k in self._token_exchange_cache if k.startswith(issuer_prefix)]
            for key in keys_to_remove:
                del self._token_exchange_cache[key]

            logger.debug(f"Cleared external IDP token cache for {issuer_url}")
        else:
            self._client_credentials_cache.clear()
            self._token_exchange_cache.clear()
            logger.debug("Cleared all external IDP token cache entries")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "client_credentials_entries": len(self._client_credentials_cache),
            "token_exchange_entries": len(self._token_exchange_cache),
            "cache_buffer_seconds": self._cache_buffer,
        }
