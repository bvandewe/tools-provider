"""Rate Limiting Middleware for WebSocket Messages.

Implements token bucket rate limiting per user per message type.
Returns system.error with retryAfter on exceed.

Rate Limits (Phase 3):
| Message Type          | Rate | Window |
|-----------------------|------|--------|
| data.message.send     | 10   | 60s    |
| data.response.submit  | 30   | 60s    |
| data.audit.events     | 10   | 60s    |
| data.tool.result      | 20   | 60s    |
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from application.protocol.core import ProtocolMessage, create_message
from application.protocol.system import SystemErrorPayload
from application.websocket.connection import Connection

log = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limits per message type."""

    max_requests: int
    window_seconds: int = 60


# Default rate limits per message type
DEFAULT_RATE_LIMITS: dict[str, RateLimitConfig] = {
    "data.message.send": RateLimitConfig(max_requests=10, window_seconds=60),
    "data.response.submit": RateLimitConfig(max_requests=30, window_seconds=60),
    "data.audit.events": RateLimitConfig(max_requests=10, window_seconds=60),
    "data.tool.result": RateLimitConfig(max_requests=20, window_seconds=60),
}


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    tokens: float
    last_update: datetime
    max_tokens: int
    refill_rate: float  # tokens per second

    @classmethod
    def create(cls, config: RateLimitConfig) -> "TokenBucket":
        """Create a new token bucket from config."""
        return cls(
            tokens=float(config.max_requests),
            last_update=datetime.now(UTC),
            max_tokens=config.max_requests,
            refill_rate=config.max_requests / config.window_seconds,
        )

    def try_consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if successful."""
        now = datetime.now(UTC)
        elapsed = (now - self.last_update).total_seconds()

        # Refill tokens based on elapsed time
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def time_until_available(self, tokens: int = 1) -> int:
        """Calculate milliseconds until tokens become available."""
        if self.tokens >= tokens:
            return 0
        needed = tokens - self.tokens
        seconds = needed / self.refill_rate
        return int(seconds * 1000)


@dataclass
class RateLimitMiddleware:
    """Rate limiting middleware for WebSocket messages.

    Uses token bucket algorithm per user per message type.
    """

    rate_limits: dict[str, RateLimitConfig] = field(default_factory=lambda: DEFAULT_RATE_LIMITS.copy())
    # Buckets: user_id -> message_type -> TokenBucket
    _buckets: dict[str, dict[str, TokenBucket]] = field(default_factory=dict)

    def get_bucket(self, user_id: str, message_type: str) -> TokenBucket | None:
        """Get or create a token bucket for user and message type."""
        config = self.rate_limits.get(message_type)
        if not config:
            return None  # No rate limit for this message type

        if user_id not in self._buckets:
            self._buckets[user_id] = {}

        if message_type not in self._buckets[user_id]:
            self._buckets[user_id][message_type] = TokenBucket.create(config)

        return self._buckets[user_id][message_type]

    async def __call__(
        self,
        connection: Connection,
        message: ProtocolMessage[Any],
        next_handler: Callable[[Connection, ProtocolMessage[Any]], Awaitable[None]],
    ) -> None:
        """Apply rate limiting before passing to next handler."""
        user_id = connection.user_id or connection.connection_id
        message_type = message.type

        bucket = self.get_bucket(user_id, message_type)

        if bucket is not None:
            if not bucket.try_consume():
                retry_after = bucket.time_until_available()
                log.warning(f"⚠️ Rate limit exceeded for {user_id[:8]}... on {message_type}, retry in {retry_after}ms")

                await self._send_rate_limit_error(connection, message_type, retry_after)
                return

        await next_handler(connection, message)

    async def _send_rate_limit_error(
        self,
        connection: Connection,
        message_type: str,
        retry_after_ms: int,
    ) -> None:
        """Send rate limit exceeded error to client."""
        error_payload = SystemErrorPayload(
            category="rate_limit",
            code="RATE_LIMIT_EXCEEDED",
            message=f"Too many {message_type} messages, please slow down",
            isRetryable=True,
            retryAfterMs=retry_after_ms,
        )
        error_message = create_message(
            message_type="system.error",
            payload=error_payload.model_dump(by_alias=True),
            conversation_id=connection.conversation_id,
        )

        try:
            message_dict = error_message.model_dump(by_alias=True, exclude_none=True)
            await connection.websocket.send_json(message_dict)
        except Exception as e:
            log.error(f"Failed to send rate limit error: {e}")

    def cleanup_stale_buckets(self, max_age_seconds: int = 3600) -> int:
        """Remove buckets that haven't been used recently.

        Args:
            max_age_seconds: Remove buckets older than this

        Returns:
            Number of buckets removed
        """
        now = datetime.now(UTC)
        removed = 0

        users_to_remove = []
        for user_id, buckets in self._buckets.items():
            types_to_remove = []
            for msg_type, bucket in buckets.items():
                age = (now - bucket.last_update).total_seconds()
                if age > max_age_seconds:
                    types_to_remove.append(msg_type)

            for msg_type in types_to_remove:
                del buckets[msg_type]
                removed += 1

            if not buckets:
                users_to_remove.append(user_id)

        for user_id in users_to_remove:
            del self._buckets[user_id]

        if removed > 0:
            log.debug(f"🧹 Cleaned up {removed} stale rate limit buckets")

        return removed


# Singleton instance for use as middleware
_rate_limit_middleware: RateLimitMiddleware | None = None


def get_rate_limit_middleware() -> RateLimitMiddleware:
    """Get or create the rate limit middleware singleton."""
    global _rate_limit_middleware
    if _rate_limit_middleware is None:
        _rate_limit_middleware = RateLimitMiddleware()
    return _rate_limit_middleware


async def rate_limit_middleware(
    connection: Connection,
    message: ProtocolMessage[Any],
    next_handler: Callable[[Connection, ProtocolMessage[Any]], Awaitable[None]],
) -> None:
    """Convenience function for use as middleware in router.

    Uses the singleton RateLimitMiddleware instance.
    """
    middleware = get_rate_limit_middleware()
    await middleware(connection, message, next_handler)
