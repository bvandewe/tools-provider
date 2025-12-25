"""Redis-backed session store for OAuth2 BFF pattern."""

import json
import logging
import secrets
from typing import Any

import redis as sync_redis
import redis.asyncio as aioredis

log = logging.getLogger(__name__)


class RedisSessionStore:
    """Redis-backed session storage for OAuth2 session management.

    Supports the BFF (Backend for Frontend) pattern with:
    - Session creation and retrieval
    - Automatic TTL management
    - Token storage with refresh support
    """

    def __init__(
        self,
        redis_url: str,
        session_ttl: int = 3600,
        prefix: str = "km:session:",
    ):
        """Initialize Redis session store.

        Args:
            redis_url: Redis connection URL
            session_ttl: Session time-to-live in seconds (default: 1 hour)
            prefix: Key prefix for session storage
        """
        # Async Redis client for async methods
        self._redis: aioredis.Redis = aioredis.from_url(redis_url, decode_responses=True)
        # Sync Redis client for synchronous methods (OAuth2 flow)
        self._redis_sync: sync_redis.Redis = sync_redis.from_url(redis_url, decode_responses=True)
        self._session_ttl = session_ttl
        self._prefix = prefix

    # =========================================================================
    # Synchronous convenience methods for controller compatibility
    # =========================================================================

    def create_session(self, tokens: dict[str, Any], user_info: dict[str, Any]) -> str:
        """Create a new session synchronously (for OAuth2 callback).

        Args:
            tokens: Token dictionary from Keycloak
            user_info: User info dictionary

        Returns:
            Session ID string
        """
        session_id = secrets.token_urlsafe(32)
        data = {
            "tokens": tokens,
            "user_info": user_info,
        }

        key = f"{self._prefix}{session_id}"
        self._redis_sync.setex(key, self._session_ttl, json.dumps(data))

        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session synchronously (for controller compatibility).

        Args:
            session_id: Session identifier

        Returns:
            Session data or None
        """
        key = f"{self._prefix}{session_id}"
        try:
            data: bytes | None = self._redis_sync.get(key)  # type: ignore[assignment]
            if data is None:
                return None
            return json.loads(data)
        except Exception as e:
            log.error(f"Failed to get session {session_id}: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete session synchronously (for controller compatibility).

        Args:
            session_id: Session identifier

        Returns:
            True if deleted
        """
        key = f"{self._prefix}{session_id}"
        try:
            result: int = self._redis_sync.delete(key)  # type: ignore[assignment]
            return result > 0
        except Exception as e:
            log.error(f"Failed to delete session {session_id}: {e}")
            return False

    def store_pkce(self, state: str, code_verifier: str) -> None:
        """Store PKCE code_verifier for OAuth2 flow.

        Uses the state parameter as the key to store the code_verifier
        temporarily. This will be retrieved in the callback.

        Args:
            state: The OAuth2 state parameter (used as key)
            code_verifier: The PKCE code verifier to store
        """
        key = f"{self._prefix}pkce:{state}"
        # PKCE data expires in 5 minutes (should be consumed quickly)
        self._redis_sync.setex(key, 300, code_verifier)

    def get_pkce(self, state: str) -> str | None:
        """Retrieve and delete PKCE code_verifier.

        Args:
            state: The OAuth2 state parameter (used as key)

        Returns:
            The code_verifier or None if not found
        """
        key = f"{self._prefix}pkce:{state}"
        verifier: bytes | str | None = self._redis_sync.get(key)  # type: ignore[assignment]
        if verifier:
            self._redis_sync.delete(key)
            # Handle both bytes and string (depends on decode_responses setting)
            if isinstance(verifier, bytes):
                return verifier.decode("utf-8")
            return verifier
        return None

    async def get(self, session_id: str) -> dict[str, Any] | None:
        """Get session data by ID.

        Args:
            session_id: The session identifier

        Returns:
            Session data dictionary or None if not found/expired
        """
        key = f"{self._prefix}{session_id}"
        try:
            data = await self._redis.get(key)
            if data is None:
                return None
            return json.loads(data)
        except Exception as e:
            log.error(f"Failed to get session {session_id}: {e}")
            return None

    async def set(
        self,
        session_id: str,
        data: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Store session data.

        Args:
            session_id: The session identifier
            data: Session data to store
            ttl: Optional custom TTL (uses default if not provided)

        Returns:
            True if successful
        """
        key = f"{self._prefix}{session_id}"
        try:
            await self._redis.setex(
                key,
                ttl or self._session_ttl,
                json.dumps(data),
            )
            return True
        except Exception as e:
            log.error(f"Failed to set session {session_id}: {e}")
            return False

    async def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The session identifier

        Returns:
            True if deleted
        """
        key = f"{self._prefix}{session_id}"
        try:
            result = await self._redis.delete(key)
            return result > 0
        except Exception as e:
            log.error(f"Failed to delete session {session_id}: {e}")
            return False

    async def refresh(self, session_id: str) -> bool:
        """Refresh session TTL.

        Args:
            session_id: The session identifier

        Returns:
            True if refreshed
        """
        key = f"{self._prefix}{session_id}"
        try:
            result = await self._redis.expire(key, self._session_ttl)
            return bool(result)
        except Exception as e:
            log.error(f"Failed to refresh session {session_id}: {e}")
            return False

    async def exists(self, session_id: str) -> bool:
        """Check if session exists.

        Args:
            session_id: The session identifier

        Returns:
            True if session exists
        """
        key = f"{self._prefix}{session_id}"
        try:
            result = await self._redis.exists(key)
            return bool(result)
        except Exception as e:
            log.error(f"Failed to check session {session_id}: {e}")
            return False

    async def update(self, session_id: str, updates: dict[str, Any]) -> bool:
        """Update specific fields in session data.

        Args:
            session_id: The session identifier
            updates: Fields to update

        Returns:
            True if successful
        """
        data = await self.get(session_id)
        if data is None:
            return False

        data.update(updates)
        return await self.set(session_id, data)

    async def close(self) -> None:
        """Close Redis connection."""
        await self._redis.close()

    async def health_check(self) -> bool:
        """Check Redis connectivity.

        Returns:
            True if Redis is healthy
        """
        try:
            await self._redis.ping()
            return True
        except Exception as e:
            log.error(f"Redis health check failed: {e}")
            return False
