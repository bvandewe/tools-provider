"""Redis session store for Agent Host user sessions."""

import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from application.settings import Settings
from neuroglia.hosting.abstractions import ApplicationBuilderBase

logger = logging.getLogger(__name__)

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore[assignment]
    REDIS_AVAILABLE = False


class RedisSessionStore:
    """
    Redis-based session store for Agent Host.

    Stores user sessions including:
    - OAuth tokens (access_token, refresh_token)
    - User info from Keycloak
    - Current conversation ID

    Uses Redis database 2 (separate from Tools Provider).
    """

    def __init__(
        self,
        redis_url: str,
        session_timeout_seconds: int = 3600,
        key_prefix: str = "agent-host:session:",
    ) -> None:
        """
        Initialize the Redis session store.

        Args:
            redis_url: Redis connection URL (e.g., redis://redis:6379/2)
            session_timeout_seconds: Session TTL in seconds (default: 1 hour)
            key_prefix: Prefix for all session keys
        """
        if not REDIS_AVAILABLE:
            raise RuntimeError("redis package is required. Install with: pip install redis")

        self._client = redis.from_url(redis_url, decode_responses=True)
        self._session_timeout_seconds = session_timeout_seconds
        self._key_prefix = key_prefix

    def _make_key(self, session_id: str) -> str:
        """Create Redis key from session ID."""
        return f"{self._key_prefix}{session_id}"

    def create_session(
        self,
        tokens: dict[str, Any],
        user_info: dict[str, Any],
    ) -> str:
        """
        Create a new session.

        Args:
            tokens: OAuth tokens (access_token, refresh_token, etc.)
            user_info: User info from Keycloak

        Returns:
            Session ID
        """
        session_id = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)

        session_data = {
            "tokens": tokens,
            "user_info": user_info,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=self._session_timeout_seconds)).isoformat(),
            "conversation_id": None,
        }

        key = self._make_key(session_id)
        self._client.setex(
            key,
            self._session_timeout_seconds,
            json.dumps(session_data),
        )

        logger.debug(f"Created session {session_id[:8]}...")
        return session_id

    def get_session(self, session_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve session data.

        Args:
            session_id: The session ID

        Returns:
            Session data or None if not found/expired
        """
        key = self._make_key(session_id)
        data = self._client.get(key)

        if not data:
            return None

        return json.loads(data)

    def get_access_token(self, session_id: str) -> Optional[str]:
        """
        Get the access token from a session.

        Args:
            session_id: The session ID

        Returns:
            Access token or None
        """
        session = self.get_session(session_id)
        if session and "tokens" in session:
            return session["tokens"].get("access_token")
        return None

    def get_user_id(self, session_id: str) -> Optional[str]:
        """
        Get the user ID from a session.

        Args:
            session_id: The session ID

        Returns:
            User ID (sub claim) or None
        """
        session = self.get_session(session_id)
        if session and "user_info" in session:
            return session["user_info"].get("sub")
        return None

    def update_tokens(
        self,
        session_id: str,
        new_tokens: dict[str, Any],
    ) -> bool:
        """
        Update session with new tokens (after refresh).

        Args:
            session_id: The session ID
            new_tokens: New token values

        Returns:
            True if updated, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False

        # Merge tokens
        existing_tokens = session.get("tokens", {})
        existing_tokens.update(new_tokens)
        session["tokens"] = existing_tokens

        # Extend expiration
        now = datetime.now(timezone.utc)
        session["expires_at"] = (now + timedelta(seconds=self._session_timeout_seconds)).isoformat()

        key = self._make_key(session_id)
        self._client.setex(
            key,
            self._session_timeout_seconds,
            json.dumps(session),
        )

        return True

    def set_conversation_id(
        self,
        session_id: str,
        conversation_id: str,
    ) -> bool:
        """
        Set the active conversation ID for a session.

        Args:
            session_id: The session ID
            conversation_id: The conversation ID

        Returns:
            True if updated, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False

        session["conversation_id"] = conversation_id

        key = self._make_key(session_id)
        ttl = self._client.ttl(key)
        if ttl > 0:
            self._client.setex(key, ttl, json.dumps(session))
        else:
            self._client.setex(key, self._session_timeout_seconds, json.dumps(session))

        return True

    def get_conversation_id(self, session_id: str) -> Optional[str]:
        """
        Get the active conversation ID for a session.

        Args:
            session_id: The session ID

        Returns:
            Conversation ID or None
        """
        session = self.get_session(session_id)
        if session:
            return session.get("conversation_id")
        return None

    def delete_session(self, session_id: str) -> None:
        """Delete a session."""
        key = self._make_key(session_id)
        self._client.delete(key)
        logger.debug(f"Deleted session {session_id[:8]}...")

    def ping(self) -> bool:
        """
        Check if Redis is healthy.

        Returns:
            True if healthy
        """
        try:
            result = self._client.ping()
            return bool(result) if not isinstance(result, bool) else result
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    @staticmethod
    def configure(builder: ApplicationBuilderBase) -> None:
        """
        Configure RedisSessionStore in the service collection.

        Args:
            builder: The application builder
        """
        settings: Settings = next(
            (d.singleton for d in builder.services if d.service_type is Settings),
            None,
        )

        if settings is None:
            logger.warning("Settings not found in services, using defaults")
            settings = Settings()

        store = RedisSessionStore(
            redis_url=settings.redis_url,
            session_timeout_seconds=settings.conversation_session_ttl_seconds,
            key_prefix=settings.redis_key_prefix,
        )

        builder.services.add_singleton(RedisSessionStore, singleton=store)
        logger.info(f"Configured RedisSessionStore with key_prefix={settings.redis_key_prefix}")
