"""Redis-based OAuth2 token cache for OpenAI provider.

This module provides token caching functionality for OAuth2 authentication
used with OpenAI-compatible endpoints (e.g., Cisco Circuit).

The token is stored in Redis with TTL based on the token's expiration time,
allowing for automatic refresh before expiry.
"""

import json
import logging
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore[assignment]
    REDIS_AVAILABLE = False


@dataclass
class CachedToken:
    """Cached OAuth2 token with metadata.

    Attributes:
        access_token: The bearer token
        token_type: Token type (usually "Bearer")
        expires_at: Unix timestamp when token expires
        scope: Token scope (if provided)
    """

    access_token: str
    token_type: str
    expires_at: float
    scope: str | None = None

    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 60s buffer)."""
        return time.time() >= (self.expires_at - 60)

    @property
    def remaining_seconds(self) -> float:
        """Get remaining seconds until expiry."""
        return max(0, self.expires_at - time.time())

    def to_dict(self) -> dict:
        """Convert to dictionary for Redis storage."""
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "scope": self.scope,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CachedToken":
        """Create from dictionary."""
        return cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_at=data["expires_at"],
            scope=data.get("scope"),
        )


class OpenAiTokenCache:
    """Redis-based cache for OpenAI OAuth2 tokens.

    Uses Redis database 2 (same as sessions) with a dedicated key prefix.
    Tokens are stored with TTL matching their expiration time.

    Thread Safety:
    - Redis operations are atomic
    - Token refresh is synchronized via Redis SETNX

    Usage:
        cache = OpenAiTokenCache(redis_url="redis://redis:6379/2")
        token = await cache.get_or_refresh_token(
            oauth_endpoint="https://id.cisco.com/oauth2/default/v1/token",
            client_id="xxx",
            client_secret="yyy",  # pragma: allowlist secret
        )
    """

    KEY_PREFIX = "agent-host:openai:token"
    LOCK_KEY = "agent-host:openai:token:lock"
    LOCK_TTL_SECONDS = 30  # Lock timeout for refresh

    def __init__(
        self,
        redis_url: str,
        default_ttl_seconds: int = 3600,
    ) -> None:
        """Initialize the token cache.

        Args:
            redis_url: Redis connection URL (e.g., redis://redis:6379/2)
            default_ttl_seconds: Default token TTL if not provided by OAuth server
        """
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis package is required. Install with: pip install redis")

        self._client = redis.from_url(redis_url, decode_responses=True)
        self._default_ttl = default_ttl_seconds
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for OAuth requests."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    def get_cached_token(self) -> CachedToken | None:
        """Get cached token if valid.

        Returns:
            CachedToken if found and not expired, None otherwise
        """
        try:
            data = self._client.get(self.KEY_PREFIX)
            if not data:
                return None

            token = CachedToken.from_dict(json.loads(data))
            if token.is_expired:
                logger.debug("Cached token is expired")
                return None

            logger.debug(f"Using cached token (expires in {token.remaining_seconds:.0f}s)")
            return token

        except Exception as e:
            logger.warning(f"Failed to get cached token: {e}")
            return None

    def cache_token(self, token: CachedToken) -> None:
        """Cache a token with appropriate TTL.

        Args:
            token: Token to cache
        """
        try:
            ttl = int(token.remaining_seconds)
            if ttl > 0:
                self._client.setex(
                    self.KEY_PREFIX,
                    ttl,
                    json.dumps(token.to_dict()),
                )
                logger.debug(f"Cached token with TTL={ttl}s")
        except Exception as e:
            logger.warning(f"Failed to cache token: {e}")

    def _acquire_refresh_lock(self) -> bool:
        """Acquire lock for token refresh (prevents concurrent refreshes).

        Returns:
            True if lock acquired, False if already held
        """
        return bool(self._client.set(self.LOCK_KEY, "1", nx=True, ex=self.LOCK_TTL_SECONDS))

    def _release_refresh_lock(self) -> None:
        """Release the refresh lock."""
        self._client.delete(self.LOCK_KEY)

    async def fetch_new_token(
        self,
        oauth_endpoint: str,
        client_id: str,
        client_secret: str,
        token_ttl: int | None = None,
    ) -> CachedToken:
        """Fetch a new OAuth2 token using client credentials grant.

        Args:
            oauth_endpoint: Token endpoint URL
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            token_ttl: Override TTL (uses server response or default if not provided)

        Returns:
            New CachedToken

        Raises:
            httpx.HTTPStatusError: If token request fails
        """
        client = await self._get_http_client()

        logger.info(f"Fetching new OAuth2 token from {oauth_endpoint}")

        response = await client.post(
            oauth_endpoint,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "client_credentials",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()

        data = response.json()
        access_token = data["access_token"]
        token_type = data.get("token_type", "Bearer")
        scope = data.get("scope")

        # Calculate expiration time
        # Priority: provided token_ttl > server expires_in > default_ttl
        expires_in = token_ttl or data.get("expires_in", self._default_ttl)
        expires_at = time.time() + expires_in

        logger.info(f"Obtained new token (expires_in={expires_in}s)")

        return CachedToken(
            access_token=access_token,
            token_type=token_type,
            expires_at=expires_at,
            scope=scope,
        )

    async def get_or_refresh_token(
        self,
        oauth_endpoint: str,
        client_id: str,
        client_secret: str,
        token_ttl: int | None = None,
        force_refresh: bool = False,
    ) -> str:
        """Get a valid token, refreshing if necessary.

        This is the main method for obtaining a token. It:
        1. Returns cached token if valid
        2. Acquires lock and refreshes if expired
        3. Caches the new token

        Args:
            oauth_endpoint: Token endpoint URL
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            token_ttl: Override TTL for caching
            force_refresh: Force token refresh even if cached

        Returns:
            Valid access token string

        Raises:
            RuntimeError: If token fetch fails
        """
        # Check cache first (unless forced refresh)
        if not force_refresh:
            cached = self.get_cached_token()
            if cached:
                return cached.access_token

        # Try to acquire lock for refresh
        if not self._acquire_refresh_lock():
            # Another process is refreshing, wait and retry cache
            logger.debug("Waiting for another process to refresh token...")
            import asyncio

            await asyncio.sleep(1)
            cached = self.get_cached_token()
            if cached:
                return cached.access_token
            # If still no token, fall through to fetch

        try:
            token = await self.fetch_new_token(
                oauth_endpoint=oauth_endpoint,
                client_id=client_id,
                client_secret=client_secret,
                token_ttl=token_ttl,
            )
            self.cache_token(token)
            return token.access_token

        except httpx.HTTPStatusError as e:
            logger.error(f"OAuth2 token request failed: {e.response.status_code} - {e.response.text}")
            raise RuntimeError(f"Failed to obtain OAuth2 token: {e.response.status_code}")

        except Exception as e:
            logger.error(f"OAuth2 token request error: {e}")
            raise RuntimeError(f"Failed to obtain OAuth2 token: {e}")

        finally:
            self._release_refresh_lock()

    def clear_cache(self) -> None:
        """Clear the cached token."""
        self._client.delete(self.KEY_PREFIX)
        logger.info("Cleared cached OpenAI token")

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    def ping(self) -> bool:
        """Check Redis connectivity.

        Returns:
            True if Redis is healthy
        """
        try:
            return bool(self._client.ping())
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False


# Singleton instance
_token_cache: OpenAiTokenCache | None = None


def get_openai_token_cache() -> OpenAiTokenCache | None:
    """Get the singleton token cache instance.

    Returns:
        OpenAiTokenCache instance or None if not initialized
    """
    return _token_cache


def set_openai_token_cache(cache: OpenAiTokenCache) -> None:
    """Set the singleton token cache instance.

    Args:
        cache: Token cache instance
    """
    global _token_cache
    _token_cache = cache
    logger.info("OpenAI token cache initialized")
