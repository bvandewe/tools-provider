"""Rate limiting service for Agent Host.

Provides per-user rate limiting to prevent abuse and manage concurrent requests.
Uses Redis for distributed rate limiting across multiple instances.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from infrastructure.session_store import RedisSessionStore

logger = logging.getLogger(__name__)


@dataclass
class ActiveRequest:
    """Represents an active streaming request."""

    request_id: str
    user_id: str
    conversation_id: str
    started_at: float = field(default_factory=time.time)
    cancelled: bool = False


class RateLimiter:
    """Rate limiter for controlling request frequency and concurrency.

    Features:
    - Per-user request rate limiting (requests per minute)
    - Per-user concurrent request limiting
    - Request cancellation tracking
    - In-memory tracking with Redis backing for distributed setups
    """

    def __init__(
        self,
        session_store: RedisSessionStore,
        requests_per_minute: int = 20,
        max_concurrent: int = 1,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            session_store: Redis session store for distributed state
            requests_per_minute: Maximum requests per user per minute
            max_concurrent: Maximum concurrent streaming requests per user
        """
        self._session_store = session_store
        self._requests_per_minute = requests_per_minute
        self._max_concurrent = max_concurrent

        # In-memory tracking for active requests (per-instance)
        # Key: user_id, Value: dict of request_id -> ActiveRequest
        self._active_requests: dict[str, dict[str, ActiveRequest]] = {}

        # Request timestamps for rate limiting (per-instance, could use Redis for distributed)
        # Key: user_id, Value: list of timestamps
        self._request_timestamps: dict[str, list[float]] = {}

        # Lock for thread-safe access
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, user_id: str) -> tuple[bool, Optional[str]]:
        """Check if a user is within rate limits.

        Args:
            user_id: The user ID to check

        Returns:
            Tuple of (is_allowed, error_message)
        """
        async with self._lock:
            now = time.time()
            window_start = now - 60  # 1 minute window

            # Clean old timestamps
            if user_id in self._request_timestamps:
                self._request_timestamps[user_id] = [ts for ts in self._request_timestamps[user_id] if ts > window_start]
            else:
                self._request_timestamps[user_id] = []

            # Check rate limit
            request_count = len(self._request_timestamps[user_id])
            if request_count >= self._requests_per_minute:
                return False, f"Rate limit exceeded. Maximum {self._requests_per_minute} requests per minute."

            return True, None

    async def check_concurrent_limit(self, user_id: str) -> tuple[bool, Optional[str]]:
        """Check if a user has reached concurrent request limit.

        Args:
            user_id: The user ID to check

        Returns:
            Tuple of (is_allowed, error_message)
        """
        async with self._lock:
            active = self._active_requests.get(user_id, {})
            # Filter out cancelled requests
            active_count = sum(1 for req in active.values() if not req.cancelled)

            if active_count >= self._max_concurrent:
                return False, "Please wait for the current response to complete before sending another message."

            return True, None

    async def start_request(
        self,
        request_id: str,
        user_id: str,
        conversation_id: str,
    ) -> ActiveRequest:
        """Register a new active request.

        Args:
            request_id: Unique request ID
            user_id: User making the request
            conversation_id: Conversation ID

        Returns:
            The ActiveRequest object for tracking
        """
        async with self._lock:
            # Record timestamp for rate limiting
            if user_id not in self._request_timestamps:
                self._request_timestamps[user_id] = []
            self._request_timestamps[user_id].append(time.time())

            # Create active request
            active_request = ActiveRequest(
                request_id=request_id,
                user_id=user_id,
                conversation_id=conversation_id,
            )

            if user_id not in self._active_requests:
                self._active_requests[user_id] = {}
            self._active_requests[user_id][request_id] = active_request

            logger.debug(f"Started request {request_id} for user {user_id}")
            return active_request

    async def end_request(self, request_id: str, user_id: str) -> None:
        """Mark a request as completed.

        Args:
            request_id: The request ID to complete
            user_id: The user ID
        """
        async with self._lock:
            if user_id in self._active_requests:
                self._active_requests[user_id].pop(request_id, None)
                logger.debug(f"Ended request {request_id} for user {user_id}")

    async def cancel_request(self, request_id: str, user_id: str) -> bool:
        """Cancel an active request.

        Args:
            request_id: The request ID to cancel
            user_id: The user ID

        Returns:
            True if request was found and cancelled, False otherwise
        """
        async with self._lock:
            if user_id in self._active_requests:
                if request_id in self._active_requests[user_id]:
                    self._active_requests[user_id][request_id].cancelled = True
                    logger.info(f"Cancelled request {request_id} for user {user_id}")
                    return True
            return False

    async def cancel_all_user_requests(self, user_id: str) -> int:
        """Cancel all active requests for a user.

        Args:
            user_id: The user ID

        Returns:
            Number of requests cancelled
        """
        async with self._lock:
            if user_id not in self._active_requests:
                return 0

            count = 0
            for request in self._active_requests[user_id].values():
                if not request.cancelled:
                    request.cancelled = True
                    count += 1

            logger.info(f"Cancelled {count} requests for user {user_id}")
            return count

    def is_cancelled(self, request_id: str, user_id: str) -> bool:
        """Check if a request has been cancelled.

        Args:
            request_id: The request ID to check
            user_id: The user ID

        Returns:
            True if cancelled, False otherwise
        """
        if user_id in self._active_requests:
            request = self._active_requests[user_id].get(request_id)
            if request:
                return request.cancelled
        return False

    async def get_active_request_count(self, user_id: str) -> int:
        """Get the number of active requests for a user.

        Args:
            user_id: The user ID

        Returns:
            Number of active (non-cancelled) requests
        """
        async with self._lock:
            if user_id not in self._active_requests:
                return 0
            return sum(1 for req in self._active_requests[user_id].values() if not req.cancelled)


# Global rate limiter instance (initialized in main.py)
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> Optional[RateLimiter]:
    """Get the global rate limiter instance."""
    return _rate_limiter


def set_rate_limiter(limiter: RateLimiter) -> None:
    """Set the global rate limiter instance."""
    global _rate_limiter
    _rate_limiter = limiter
