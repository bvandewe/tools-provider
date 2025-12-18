"""OIDC Discovery Service.

Handles fetching and caching OpenID Connect discovery documents from
identity providers. Used to discover token endpoints, JWKS URLs, and
other OIDC metadata for external IDPs.

Key Features:
- Fetches .well-known/openid-configuration documents
- Caches discovery documents with configurable TTL
- Async-safe with proper error handling
- Comprehensive observability (tracing, logging)

Usage:
    discovery = OIDCDiscoveryService()

    # Get discovery document
    config = await discovery.get_discovery_document(
        issuer_url="https://keycloak.example.com/realms/myrealm"
    )

    # Access endpoints
    token_url = config.token_endpoint
    jwks_uri = config.jwks_uri
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


@dataclass(frozen=True)
class OIDCDiscoveryDocument:
    """OIDC Discovery Document (OpenID Connect Discovery 1.0).

    Contains the essential endpoints and metadata from an OIDC provider's
    .well-known/openid-configuration document.

    Attributes:
        issuer: The Issuer Identifier URL
        authorization_endpoint: OAuth2 authorization endpoint
        token_endpoint: OAuth2 token endpoint
        userinfo_endpoint: OIDC UserInfo endpoint
        jwks_uri: URL of the JWKS (JSON Web Key Set)
        scopes_supported: List of supported OAuth2 scopes
        response_types_supported: Supported OAuth2 response types
        grant_types_supported: Supported OAuth2 grant types
        token_endpoint_auth_methods_supported: Token endpoint auth methods
        raw_document: Complete raw discovery document for additional claims
    """

    issuer: str
    token_endpoint: str
    jwks_uri: str
    authorization_endpoint: str | None = None
    userinfo_endpoint: str | None = None
    scopes_supported: list[str] = field(default_factory=list)
    response_types_supported: list[str] = field(default_factory=list)
    grant_types_supported: list[str] = field(default_factory=list)
    token_endpoint_auth_methods_supported: list[str] = field(default_factory=list)
    raw_document: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OIDCDiscoveryDocument":
        """Create OIDCDiscoveryDocument from raw discovery response.

        Args:
            data: Raw JSON response from .well-known/openid-configuration

        Returns:
            Parsed OIDCDiscoveryDocument

        Raises:
            ValueError: If required fields are missing
        """
        issuer = data.get("issuer")
        token_endpoint = data.get("token_endpoint")
        jwks_uri = data.get("jwks_uri")

        if not issuer:
            raise ValueError("Discovery document missing required field: issuer")
        if not token_endpoint:
            raise ValueError("Discovery document missing required field: token_endpoint")
        if not jwks_uri:
            raise ValueError("Discovery document missing required field: jwks_uri")

        return cls(
            issuer=issuer,
            token_endpoint=token_endpoint,
            jwks_uri=jwks_uri,
            authorization_endpoint=data.get("authorization_endpoint"),
            userinfo_endpoint=data.get("userinfo_endpoint"),
            scopes_supported=data.get("scopes_supported", []),
            response_types_supported=data.get("response_types_supported", []),
            grant_types_supported=data.get("grant_types_supported", []),
            token_endpoint_auth_methods_supported=data.get("token_endpoint_auth_methods_supported", []),
            raw_document=data,
        )

    def supports_grant_type(self, grant_type: str) -> bool:
        """Check if the IDP supports a specific OAuth2 grant type.

        Args:
            grant_type: Grant type to check (e.g., "client_credentials", "urn:ietf:params:oauth:grant-type:token-exchange")

        Returns:
            True if grant type is supported
        """
        # If grant_types_supported is empty, assume standard grants are supported
        if not self.grant_types_supported:
            return grant_type in ("authorization_code", "client_credentials", "refresh_token")
        return grant_type in self.grant_types_supported

    def supports_token_exchange(self) -> bool:
        """Check if the IDP supports RFC 8693 Token Exchange.

        Returns:
            True if token exchange grant type is supported
        """
        return self.supports_grant_type("urn:ietf:params:oauth:grant-type:token-exchange")


@dataclass
class OIDCDiscoveryError(Exception):
    """Error during OIDC discovery.

    Attributes:
        message: Human-readable error message
        issuer_url: The issuer URL that failed
        status_code: HTTP status code (if applicable)
        is_retryable: Whether the error might succeed on retry
    """

    message: str
    issuer_url: str
    status_code: int | None = None
    is_retryable: bool = False

    def __str__(self) -> str:
        return f"{self.message} (issuer: {self.issuer_url})"


@dataclass
class _CacheEntry:
    """Internal cache entry for discovery documents."""

    document: OIDCDiscoveryDocument
    fetched_at: float  # Unix timestamp
    ttl_seconds: int


class OIDCDiscoveryService:
    """Service for fetching and caching OIDC discovery documents.

    Implements OpenID Connect Discovery 1.0 for retrieving provider metadata
    from external identity providers.

    Features:
    - Automatic caching with configurable TTL
    - Thread-safe async operations
    - Comprehensive error handling and logging
    - Observability via OpenTelemetry tracing

    Example:
        service = OIDCDiscoveryService(default_cache_ttl=3600)

        # Get discovery document
        doc = await service.get_discovery_document(
            "https://keycloak.example.com/realms/myrealm"
        )

        # Use the token endpoint
        token_url = doc.token_endpoint
    """

    def __init__(
        self,
        http_timeout: float = 10.0,
        default_cache_ttl: int = 3600,
    ) -> None:
        """Initialize the OIDC discovery service.

        Args:
            http_timeout: HTTP request timeout in seconds
            default_cache_ttl: Default cache TTL in seconds (1 hour)
        """
        self._http_timeout = http_timeout
        self._default_cache_ttl = default_cache_ttl
        self._cache: dict[str, _CacheEntry] = {}
        self._lock = asyncio.Lock()

        logger.info(f"OIDCDiscoveryService initialized (cache TTL: {default_cache_ttl}s)")

    def _build_discovery_url(self, issuer_url: str) -> str:
        """Build the .well-known/openid-configuration URL from issuer.

        Args:
            issuer_url: OIDC issuer URL (e.g., https://keycloak.example.com/realms/myrealm)

        Returns:
            Full discovery endpoint URL
        """
        issuer = issuer_url.rstrip("/")
        return f"{issuer}/.well-known/openid-configuration"

    def _is_cache_valid(self, entry: _CacheEntry) -> bool:
        """Check if a cache entry is still valid.

        Args:
            entry: Cache entry to check

        Returns:
            True if cache entry is still valid
        """
        age = time.time() - entry.fetched_at
        return age < entry.ttl_seconds

    async def get_discovery_document(
        self,
        issuer_url: str,
        skip_cache: bool = False,
        cache_ttl: int | None = None,
    ) -> OIDCDiscoveryDocument:
        """Fetch the OIDC discovery document for an issuer.

        Retrieves the OpenID Connect discovery document from the issuer's
        .well-known/openid-configuration endpoint. Results are cached.

        Args:
            issuer_url: OIDC issuer URL (e.g., https://keycloak.example.com/realms/myrealm)
            skip_cache: If True, bypass cache and fetch fresh document
            cache_ttl: Custom cache TTL for this fetch (overrides default)

        Returns:
            OIDCDiscoveryDocument with provider metadata

        Raises:
            OIDCDiscoveryError: If discovery fails
        """
        with tracer.start_as_current_span("oidc_discovery") as span:
            span.set_attribute("oidc.issuer_url", issuer_url)

            # Normalize issuer URL for cache key
            cache_key = issuer_url.rstrip("/")

            # Check cache
            if not skip_cache:
                async with self._lock:
                    entry = self._cache.get(cache_key)
                    if entry and self._is_cache_valid(entry):
                        span.set_attribute("oidc.cache_hit", True)
                        logger.debug(f"OIDC discovery cache hit for {issuer_url}")
                        return entry.document

            span.set_attribute("oidc.cache_hit", False)

            # Fetch discovery document
            discovery_url = self._build_discovery_url(issuer_url)
            span.set_attribute("oidc.discovery_url", discovery_url)

            try:
                async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                    response = await client.get(discovery_url)

                    if response.status_code == 200:
                        data = response.json()
                        document = OIDCDiscoveryDocument.from_dict(data)

                        # Cache the document
                        ttl = cache_ttl or self._default_cache_ttl
                        async with self._lock:
                            self._cache[cache_key] = _CacheEntry(
                                document=document,
                                fetched_at=time.time(),
                                ttl_seconds=ttl,
                            )

                        span.set_attribute("oidc.token_endpoint", document.token_endpoint)
                        span.set_attribute("oidc.jwks_uri", document.jwks_uri)
                        logger.info(f"OIDC discovery successful for {issuer_url}")
                        return document

                    else:
                        # Handle error responses
                        is_retryable = response.status_code in (502, 503, 504)
                        logger.warning(f"OIDC discovery failed: status={response.status_code} for {issuer_url}")

                        raise OIDCDiscoveryError(
                            message=f"OIDC discovery failed with status {response.status_code}",
                            issuer_url=issuer_url,
                            status_code=response.status_code,
                            is_retryable=is_retryable,
                        )

            except httpx.TimeoutException:
                logger.warning(f"OIDC discovery timeout for {issuer_url}")
                raise OIDCDiscoveryError(
                    message="OIDC discovery request timed out",
                    issuer_url=issuer_url,
                    is_retryable=True,
                )
            except httpx.RequestError as e:
                logger.warning(f"OIDC discovery request error for {issuer_url}: {e}")
                raise OIDCDiscoveryError(
                    message=f"OIDC discovery request failed: {e}",
                    issuer_url=issuer_url,
                    is_retryable=True,
                )
            except ValueError as e:
                logger.warning(f"OIDC discovery parse error for {issuer_url}: {e}")
                raise OIDCDiscoveryError(
                    message=f"Invalid OIDC discovery document: {e}",
                    issuer_url=issuer_url,
                    is_retryable=False,
                )

    async def get_token_endpoint(self, issuer_url: str) -> str:
        """Get the token endpoint for an issuer.

        Convenience method that fetches the discovery document and returns
        just the token endpoint URL.

        Args:
            issuer_url: OIDC issuer URL

        Returns:
            Token endpoint URL

        Raises:
            OIDCDiscoveryError: If discovery fails
        """
        document = await self.get_discovery_document(issuer_url)
        return document.token_endpoint

    async def get_jwks_uri(self, issuer_url: str) -> str:
        """Get the JWKS URI for an issuer.

        Convenience method that fetches the discovery document and returns
        just the JWKS URI.

        Args:
            issuer_url: OIDC issuer URL

        Returns:
            JWKS URI

        Raises:
            OIDCDiscoveryError: If discovery fails
        """
        document = await self.get_discovery_document(issuer_url)
        return document.jwks_uri

    def clear_cache(self, issuer_url: str | None = None) -> None:
        """Clear cached discovery documents.

        Args:
            issuer_url: Specific issuer to clear, or None to clear all
        """
        if issuer_url:
            cache_key = issuer_url.rstrip("/")
            self._cache.pop(cache_key, None)
            logger.debug(f"Cleared OIDC discovery cache for {issuer_url}")
        else:
            self._cache.clear()
            logger.debug("Cleared all OIDC discovery cache entries")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics
        """
        valid_entries = sum(1 for entry in self._cache.values() if self._is_cache_valid(entry))
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "issuers": list(self._cache.keys()),
        }
