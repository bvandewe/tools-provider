"""Keycloak Token Exchanger implementing RFC 8693 Token Exchange.

This adapter handles exchanging agent access tokens for upstream service tokens,
enabling secure delegation of identity when proxying tool execution requests.

Key Features:
- RFC 8693 compliant token exchange
- Token caching with configurable TTL
- Circuit breaker for resilience
- Comprehensive observability (tracing, metrics, logging)
- CloudEvent emission for circuit breaker state changes

Security Considerations:
- Uses a dedicated confidential client for token exchange operations
- Caches tokens with TTL less than actual expiry for safety
- Never logs token values, only metadata
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, cast

import httpx
from domain.events.circuit_breaker import CircuitBreakerClosedDomainEvent, CircuitBreakerHalfOpenedDomainEvent, CircuitBreakerOpenedDomainEvent, CircuitBreakerTransitionReason
from opentelemetry import trace

if TYPE_CHECKING:
    from neuroglia.hosting.web import WebApplicationBuilder

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class TokenExchangeResult:
    """Result of a token exchange operation.

    Attributes:
        access_token: The exchanged access token for the upstream service
        token_type: Token type (usually "Bearer")
        expires_in: Token lifetime in seconds
        expires_at: Absolute expiry time (UTC)
        scope: Granted scopes (may differ from requested)
        issued_token_type: Type of issued token per RFC 8693
    """

    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 300
    expires_at: Optional[datetime] = None
    scope: Optional[str] = None
    issued_token_type: str = "urn:ietf:params:oauth:token-type:access_token"

    def __post_init__(self) -> None:
        """Calculate absolute expiry time if not set."""
        if self.expires_at is None:
            self.expires_at = datetime.now(timezone.utc).replace(microsecond=0) + __import__("datetime").timedelta(seconds=self.expires_in)

    def is_expired(self, leeway_seconds: int = 30) -> bool:
        """Check if token is expired or about to expire.

        Args:
            leeway_seconds: Consider expired if within this many seconds of expiry

        Returns:
            True if token should be refreshed
        """
        if self.expires_at is None:
            return True
        threshold = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=leeway_seconds)
        return bool(self.expires_at <= threshold)


@dataclass
class TokenExchangeError(Exception):
    """Error during token exchange operation.

    Attributes:
        message: Human-readable error message
        error_code: OAuth2 error code (e.g., "invalid_grant", "invalid_target")
        error_description: Detailed error description from Keycloak
        status_code: HTTP status code from Keycloak
        is_retryable: Whether the error might succeed on retry
    """

    message: str
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    status_code: Optional[int] = None
    is_retryable: bool = False

    def __str__(self) -> str:
        parts = [self.message]
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        if self.error_description:
            parts.append(f": {self.error_description}")
        return " ".join(parts)


@dataclass
class CircuitBreaker:
    """Simple circuit breaker for external service calls.

    Protects against cascading failures by temporarily rejecting
    requests when the external service is consistently failing.

    Supports event callbacks for CloudEvent emission on state transitions.
    """

    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: float = 30.0  # Seconds before trying again
    half_open_max_calls: int = 3  # Test calls in half-open state

    # Identity for event emission
    circuit_id: str = field(default="unknown")
    circuit_type: str = field(default="unknown")
    source_id: Optional[str] = field(default=None)

    # Event callback (set by containing service to publish events)
    on_state_change: Optional[Callable[[Any], Awaitable[None]]] = field(default=None, repr=False)

    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    failure_count: int = field(default=0, init=False)
    last_failure_time: Optional[float] = field(default=None, init=False)
    half_open_calls: int = field(default=0, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    async def _emit_event(self, event: Any) -> None:
        """Emit a circuit breaker state change event."""
        if self.on_state_change:
            try:
                await self.on_state_change(event)
            except Exception as e:
                logger.warning(f"Failed to emit circuit breaker event: {e}")

    async def call(self, func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
        """Execute a function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to the function

        Returns:
            Result from the function

        Raises:
            TokenExchangeError: If circuit is open or call fails
        """
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info("Circuit breaker entering half-open state")

                    # Emit half-open event
                    await self._emit_event(
                        CircuitBreakerHalfOpenedDomainEvent(
                            circuit_id=self.circuit_id,
                            circuit_type=self.circuit_type,
                            source_id=self.source_id,
                            recovery_timeout=self.recovery_timeout,
                            opened_at=datetime.now(timezone.utc),
                        )
                    )
                else:
                    raise TokenExchangeError(
                        message="Circuit breaker is open - token exchange temporarily unavailable",
                        error_code="circuit_open",
                        is_retryable=True,
                    )

            if self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    # Too many test calls, stay half-open
                    raise TokenExchangeError(
                        message="Circuit breaker is testing - please wait",
                        error_code="circuit_testing",
                        is_retryable=True,
                    )
                self.half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception:
            await self._on_failure()
            raise

    async def _on_success(self) -> None:
        """Record successful call."""
        async with self._lock:
            was_half_open = self.state == CircuitState.HALF_OPEN

            if was_half_open:
                logger.info("Circuit breaker closing after successful test call")

            self.failure_count = 0
            self.state = CircuitState.CLOSED

            # Emit closed event if transitioning from half-open
            if was_half_open:
                await self._emit_event(
                    CircuitBreakerClosedDomainEvent(
                        circuit_id=self.circuit_id,
                        circuit_type=self.circuit_type,
                        source_id=self.source_id,
                        reason=CircuitBreakerTransitionReason.TEST_CALL_SUCCEEDED,
                        closed_at=datetime.now(timezone.utc),
                        was_manual=False,
                        closed_by=None,
                    )
                )

    async def _on_failure(self) -> None:
        """Record failed call."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                logger.warning("Circuit breaker reopened after failed test call")

                # Emit opened event
                await self._emit_event(
                    CircuitBreakerOpenedDomainEvent(
                        circuit_id=self.circuit_id,
                        circuit_type=self.circuit_type,
                        source_id=self.source_id,
                        failure_count=self.failure_count,
                        failure_threshold=self.failure_threshold,
                        last_failure_time=datetime.now(timezone.utc),
                        reason=CircuitBreakerTransitionReason.TEST_CALL_FAILED,
                    )
                )
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

                # Emit opened event
                await self._emit_event(
                    CircuitBreakerOpenedDomainEvent(
                        circuit_id=self.circuit_id,
                        circuit_type=self.circuit_type,
                        source_id=self.source_id,
                        failure_count=self.failure_count,
                        failure_threshold=self.failure_threshold,
                        last_failure_time=datetime.now(timezone.utc),
                        reason=CircuitBreakerTransitionReason.FAILURE_THRESHOLD_REACHED,
                    )
                )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try again."""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout

    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state for monitoring."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "circuit_id": self.circuit_id,
            "circuit_type": self.circuit_type,
            "source_id": self.source_id,
        }

    async def reset(self, manual: bool = False, reset_by: Optional[str] = None) -> None:
        """Manually reset the circuit breaker to closed state.

        This allows administrators to force the circuit breaker closed
        after resolving the underlying issue. Use with caution - if the
        underlying problem isn't fixed, the circuit will open again.

        Args:
            manual: Whether this is a manual reset (vs programmatic)
            reset_by: Username of admin who triggered the reset
        """
        async with self._lock:
            previous_state = self.state.value
            was_open = self.state != CircuitState.CLOSED

            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            self.half_open_calls = 0

            logger.info(f"Circuit breaker manually reset from '{previous_state}' to 'closed'" + (f" by {reset_by}" if reset_by else ""))

            # Emit closed event if was open/half-open
            if was_open:
                await self._emit_event(
                    CircuitBreakerClosedDomainEvent(
                        circuit_id=self.circuit_id,
                        circuit_type=self.circuit_type,
                        source_id=self.source_id,
                        reason=CircuitBreakerTransitionReason.MANUAL_RESET,
                        closed_at=datetime.now(timezone.utc),
                        was_manual=manual,
                        closed_by=reset_by,
                    )
                )


class KeycloakTokenExchanger:
    """RFC 8693 Token Exchange implementation for Keycloak.

    This service exchanges an agent's access token for a new token
    scoped to a specific upstream service (audience). This enables
    secure delegation of identity when proxying tool execution requests.

    Token Exchange Flow:
    1. Agent authenticates with their own credentials
    2. Agent calls /tools/call with their access token
    3. This service exchanges agent token for upstream service token
    4. Tool executor uses upstream token to call the actual API

    Configuration:
    - Requires a confidential client in Keycloak with token-exchange permission
    - Target audiences (upstream services) must be configured as clients
    - The exchange client needs permission to exchange for each target

    Caching:
    - Exchanged tokens are cached by (subject_token_hash, audience) tuple
    - Cache TTL is configurable (default: token_expiry - 60 seconds)
    - Redis is used for distributed caching across instances

    Circuit Breaker:
    - Opens after consecutive failures to protect against Keycloak outages
    - Automatically retries after recovery timeout
    """

    # Token type URNs per RFC 8693 (standard identifiers, not secrets)
    ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"  # nosec B105
    REFRESH_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:refresh_token"  # nosec B105
    ID_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:id_token"  # nosec B105
    JWT_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:jwt"  # nosec B105

    def __init__(
        self,
        keycloak_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        cache_service: Optional[Any] = None,
        cache_ttl_buffer_seconds: int = 60,
        http_timeout: float = 10.0,
        circuit_failure_threshold: int = 5,
        circuit_recovery_timeout: float = 30.0,
        on_circuit_state_change: Optional[Callable[[Any], Awaitable[None]]] = None,
    ):
        """Initialize the token exchanger.

        Args:
            keycloak_url: Base URL of Keycloak (internal URL preferred)
            realm: Keycloak realm name
            client_id: Client ID of the token exchange client
            client_secret: Client secret for authentication
            cache_service: Optional RedisCacheService for token caching
            cache_ttl_buffer_seconds: Seconds to subtract from token expiry for cache TTL
            http_timeout: HTTP request timeout in seconds
            circuit_failure_threshold: Failures before circuit opens
            circuit_recovery_timeout: Seconds before circuit retries
            on_circuit_state_change: Optional callback for circuit breaker events
        """
        self._keycloak_url = keycloak_url.rstrip("/")
        self._realm = realm
        self._client_id = client_id
        self._client_secret = client_secret
        self._cache = cache_service
        self._cache_ttl_buffer = cache_ttl_buffer_seconds
        self._http_timeout = http_timeout

        # Token endpoint
        self._token_endpoint = f"{self._keycloak_url}/realms/{self._realm}/protocol/openid-connect/token"

        # Circuit breaker with identity for event tracking
        self._circuit = CircuitBreaker(
            failure_threshold=circuit_failure_threshold,
            recovery_timeout=circuit_recovery_timeout,
            circuit_id="keycloak",
            circuit_type="token_exchange",
            source_id=None,
            on_state_change=on_circuit_state_change,
        )

        # In-memory cache fallback (per-instance)
        self._local_cache: Dict[str, TokenExchangeResult] = {}

        logger.info(f"KeycloakTokenExchanger initialized for realm '{realm}' at {keycloak_url}")

    async def exchange_token(
        self,
        subject_token: str,
        audience: str,
        requested_scopes: Optional[List[str]] = None,
        skip_cache: bool = False,
    ) -> TokenExchangeResult:
        """Exchange an access token for a new token scoped to a specific audience.

        This implements the RFC 8693 token exchange grant type.

        Args:
            subject_token: The agent's access token to exchange
            audience: Target audience (client_id of upstream service)
            requested_scopes: Optional scopes to request (default: None = all allowed)
            skip_cache: If True, bypass cache and perform fresh exchange

        Returns:
            TokenExchangeResult with the new access token

        Raises:
            TokenExchangeError: If exchange fails
        """
        with tracer.start_as_current_span("exchange_token") as span:
            span.set_attribute("token_exchange.audience", audience)
            span.set_attribute("token_exchange.skip_cache", skip_cache)

            # Generate cache key
            cache_key = self._generate_cache_key(subject_token, audience, requested_scopes)

            # Try cache first
            if not skip_cache:
                cached = await self._get_cached_token(cache_key)
                if cached and not cached.is_expired(leeway_seconds=self._cache_ttl_buffer):
                    span.set_attribute("token_exchange.cache_hit", True)
                    logger.debug(f"Token exchange cache hit for audience '{audience}'")
                    return cached
                span.set_attribute("token_exchange.cache_hit", False)

            # Perform exchange with circuit breaker protection
            span.add_event("Performing token exchange")
            result: TokenExchangeResult = cast(
                TokenExchangeResult,
                await self._circuit.call(
                    self._do_exchange,
                    subject_token=subject_token,
                    audience=audience,
                    requested_scopes=requested_scopes,
                ),
            )

            # Cache the result
            await self._cache_token(cache_key, result)

            span.set_attribute("token_exchange.expires_in", result.expires_in)
            logger.info(f"Token exchange successful for audience '{audience}', expires in {result.expires_in}s")
            return result

    async def _do_exchange(
        self,
        subject_token: str,
        audience: str,
        requested_scopes: Optional[List[str]] = None,
    ) -> TokenExchangeResult:
        """Perform the actual token exchange request.

        Args:
            subject_token: The agent's access token
            audience: Target audience
            requested_scopes: Optional scopes to request

        Returns:
            TokenExchangeResult with the exchanged token

        Raises:
            TokenExchangeError: If exchange fails
        """
        # Build request body per RFC 8693
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "subject_token": subject_token,
            "subject_token_type": self.ACCESS_TOKEN_TYPE,
            "audience": audience,
            "requested_token_type": self.ACCESS_TOKEN_TYPE,
        }

        if requested_scopes:
            data["scope"] = " ".join(requested_scopes)

        try:
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                response = await client.post(
                    self._token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code == 200:
                    token_data = response.json()
                    return TokenExchangeResult(
                        access_token=token_data["access_token"],
                        token_type=token_data.get("token_type", "Bearer"),
                        expires_in=token_data.get("expires_in", 300),
                        scope=token_data.get("scope"),
                        issued_token_type=token_data.get(
                            "issued_token_type",
                            self.ACCESS_TOKEN_TYPE,
                        ),
                    )
                else:
                    # Parse error response
                    error_data = {}
                    try:
                        error_data = response.json()
                    except Exception as parse_err:
                        logger.debug(f"Could not parse error response as JSON: {parse_err}")

                    error_code = error_data.get("error", "unknown_error")
                    error_description = error_data.get("error_description", "Token exchange failed")

                    # Determine if retryable
                    is_retryable = response.status_code in (502, 503, 504) or error_code in (
                        "temporarily_unavailable",
                        "server_error",
                    )

                    logger.warning(f"Token exchange failed: status={response.status_code}, " f"error={error_code}, description={error_description}")

                    raise TokenExchangeError(
                        message=f"Token exchange failed for audience '{audience}'",
                        error_code=error_code,
                        error_description=error_description,
                        status_code=response.status_code,
                        is_retryable=is_retryable,
                    )

        except httpx.TimeoutException as e:
            logger.error(f"Token exchange timeout: {e}")
            raise TokenExchangeError(
                message="Token exchange request timed out",
                error_code="timeout",
                is_retryable=True,
            )
        except httpx.RequestError as e:
            logger.error(f"Token exchange request error: {e}")
            raise TokenExchangeError(
                message=f"Token exchange request failed: {e}",
                error_code="request_error",
                is_retryable=True,
            )
        except TokenExchangeError:
            raise
        except Exception as e:
            logger.error(f"Unexpected token exchange error: {e}")
            raise TokenExchangeError(
                message=f"Unexpected error during token exchange: {e}",
                error_code="internal_error",
                is_retryable=False,
            )

    def _generate_cache_key(
        self,
        subject_token: str,
        audience: str,
        scopes: Optional[List[str]] = None,
    ) -> str:
        """Generate a deterministic cache key for token exchange result.

        Uses SHA256 hash of subject token to avoid storing the actual token.

        Args:
            subject_token: The agent's access token
            audience: Target audience
            scopes: Requested scopes

        Returns:
            Cache key string
        """
        # Hash the subject token (don't store actual token in cache key)
        token_hash = hashlib.sha256(subject_token.encode()).hexdigest()[:16]
        scope_str = ",".join(sorted(scopes)) if scopes else ""
        return f"token_exchange:{token_hash}:{audience}:{scope_str}"

    async def _get_cached_token(self, cache_key: str) -> Optional[TokenExchangeResult]:
        """Retrieve token from cache.

        Args:
            cache_key: Cache key

        Returns:
            Cached TokenExchangeResult or None
        """
        # Try Redis cache first
        if self._cache:
            try:
                key = f"mcp:exchange:{cache_key}"
                data = await self._cache.client.get(key)
                if data:
                    token_dict = json.loads(data)
                    return TokenExchangeResult(
                        access_token=token_dict["access_token"],
                        token_type=token_dict.get("token_type", "Bearer"),
                        expires_in=token_dict.get("expires_in", 300),
                        expires_at=datetime.fromisoformat(token_dict["expires_at"]) if token_dict.get("expires_at") else None,
                        scope=token_dict.get("scope"),
                        issued_token_type=token_dict.get("issued_token_type", self.ACCESS_TOKEN_TYPE),
                    )
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        # Fall back to local cache
        cached = self._local_cache.get(cache_key)
        if cached and not cached.is_expired(leeway_seconds=self._cache_ttl_buffer):
            return cached

        return None

    async def _cache_token(self, cache_key: str, result: TokenExchangeResult) -> None:
        """Store token in cache.

        Args:
            cache_key: Cache key
            result: Token exchange result to cache
        """
        # Calculate TTL (token expiry minus buffer)
        ttl = max(result.expires_in - self._cache_ttl_buffer, 30)

        # Store in local cache
        self._local_cache[cache_key] = result

        # Clean up expired entries from local cache periodically
        self._cleanup_local_cache()

        # Try Redis cache
        if self._cache:
            try:
                key = f"mcp:exchange:{cache_key}"
                token_dict = {
                    "access_token": result.access_token,
                    "token_type": result.token_type,
                    "expires_in": result.expires_in,
                    "expires_at": result.expires_at.isoformat() if result.expires_at else None,
                    "scope": result.scope,
                    "issued_token_type": result.issued_token_type,
                }
                await self._cache.client.set(key, json.dumps(token_dict), ex=ttl)
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")

    def _cleanup_local_cache(self) -> None:
        """Remove expired entries from local cache."""
        expired_keys = [key for key, result in self._local_cache.items() if result.is_expired(leeway_seconds=0)]
        for key in expired_keys:
            del self._local_cache[key]

    async def invalidate_cache(self, audience: Optional[str] = None) -> int:
        """Invalidate cached tokens.

        Args:
            audience: If provided, only invalidate tokens for this audience.
                     If None, invalidate all cached tokens.

        Returns:
            Number of cache entries invalidated
        """
        count = 0

        # Clear local cache
        if audience:
            keys_to_remove = [k for k in self._local_cache.keys() if f":{audience}:" in k]
            for key in keys_to_remove:
                del self._local_cache[key]
                count += 1
        else:
            count = len(self._local_cache)
            self._local_cache.clear()

        # Clear Redis cache
        if self._cache:
            try:
                pattern = f"mcp:exchange:*{':' + audience + ':' if audience else ''}*"
                keys = []
                async for key in self._cache.client.scan_iter(pattern):
                    keys.append(key)
                if keys:
                    await self._cache.client.delete(*keys)
                    count += len(keys)
            except Exception as e:
                logger.warning(f"Redis cache invalidation failed: {e}")

        logger.info(f"Invalidated {count} cached exchange tokens")
        return count

    def get_circuit_state(self) -> Dict[str, Any]:
        """Get circuit breaker state for health checks.

        Returns:
            Dict with circuit breaker status
        """
        return self._circuit.get_state()

    async def reset_circuit_breaker(self, reset_by: Optional[str] = None) -> Dict[str, Any]:
        """Manually reset the circuit breaker to closed state.

        This allows administrators to force the circuit breaker closed
        after resolving the underlying issue (e.g., Keycloak is back online).

        Args:
            reset_by: Username of admin who triggered the reset

        Returns:
            Dict with the new circuit breaker state
        """
        await self._circuit.reset(manual=True, reset_by=reset_by)
        return self._circuit.get_state()

    async def health_check(self) -> Dict[str, Any]:
        """Check health of token exchange service.

        Returns:
            Dict with health status and details
        """
        circuit_state = self.get_circuit_state()
        return {
            "healthy": circuit_state["state"] != CircuitState.OPEN.value,
            "circuit_breaker": circuit_state,
            "token_endpoint": self._token_endpoint,
            "local_cache_size": len(self._local_cache),
        }

    # =========================================================================
    # Service Configuration (Neuroglia Pattern)
    # =========================================================================

    @staticmethod
    def configure(builder: "WebApplicationBuilder") -> "WebApplicationBuilder":
        """Configure and register the Keycloak token exchanger.

        This method follows the Neuroglia pattern for service configuration,
        creating a singleton instance and registering it in the DI container.

        Resolves RedisCacheService and CircuitBreakerEventPublisher from the DI container if available.

        Args:
            builder: WebApplicationBuilder instance for service registration

        Returns:
            The builder instance for fluent chaining
        """
        from application.settings import app_settings
        from infrastructure.cache import RedisCacheService
        from infrastructure.services import CircuitBreakerEventPublisher

        log = logging.getLogger(__name__)
        log.info("🔧 Configuring KeycloakTokenExchanger...")

        # Resolve optional cache service from registered singletons
        cache_service: Optional[RedisCacheService] = None
        for desc in builder.services:
            if desc.service_type == RedisCacheService and desc.singleton is not None:
                cache_service = desc.singleton
                break

        if cache_service:
            log.debug("Found RedisCacheService in DI container")
        else:
            log.debug("RedisCacheService not available, token caching will use local cache only")

        # Resolve optional circuit breaker event publisher
        event_publisher: Optional[CircuitBreakerEventPublisher] = None
        for desc in builder.services:
            if desc.service_type == CircuitBreakerEventPublisher and desc.singleton is not None:
                event_publisher = desc.singleton
                break

        on_circuit_state_change = event_publisher.publish_event if event_publisher else None
        if event_publisher:
            log.debug("Found CircuitBreakerEventPublisher in DI container")
        else:
            log.debug("CircuitBreakerEventPublisher not available, circuit breaker events will not be published")

        token_exchanger = KeycloakTokenExchanger(
            keycloak_url=app_settings.keycloak_url_internal or app_settings.keycloak_url,
            realm=app_settings.keycloak_realm,
            client_id=app_settings.token_exchange_client_id,
            client_secret=app_settings.token_exchange_client_secret,
            cache_service=cache_service,
            cache_ttl_buffer_seconds=app_settings.token_exchange_cache_ttl_buffer,
            http_timeout=app_settings.token_exchange_timeout,
            circuit_failure_threshold=app_settings.circuit_breaker_failure_threshold,
            circuit_recovery_timeout=app_settings.circuit_breaker_recovery_timeout,
            on_circuit_state_change=on_circuit_state_change,
        )
        builder.services.add_singleton(KeycloakTokenExchanger, singleton=token_exchanger)
        log.info(f"✅ KeycloakTokenExchanger configured for realm '{app_settings.keycloak_realm}'")

        return builder
