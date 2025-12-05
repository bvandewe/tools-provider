"""Redis cache service for tool definitions and manifests.

This service provides caching capabilities for:
- Tool definitions (hot data for fast lookups)
- Group manifests (pre-computed tool lists per group)
- Agent access cache (claim-based group mappings)
- SSE pub/sub for real-time notifications
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set

import redis.asyncio as redis
from redis.asyncio.client import PubSub

logger = logging.getLogger(__name__)


class RedisCacheService:
    """Redis-based caching service for MCP Tools Provider.

    Provides:
    - Key-value caching for tool definitions and manifests
    - Pub/Sub for SSE notifications
    - Atomic operations for cache invalidation

    Key naming conventions:
    - tool:{tool_id} - Individual tool definition
    - manifest:group:{group_id} - Resolved tool list for a group
    - access:{claims_hash} - Cached group IDs for agent claims
    - source:{source_id}:tools - Set of tool IDs for a source
    """

    # Cache TTL defaults (in seconds)
    DEFAULT_TOOL_TTL = 3600  # 1 hour
    DEFAULT_MANIFEST_TTL = 1800  # 30 minutes
    DEFAULT_ACCESS_TTL = 300  # 5 minutes

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        key_prefix: str = "mcp",
    ):
        """Initialize the Redis cache service.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all cache keys (default: "mcp")
        """
        self._redis_url = redis_url
        self._key_prefix = key_prefix
        self._redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if self._redis is None:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info(f"Connected to Redis at {self._redis_url}")

    async def disconnect(self) -> None:
        """Close the Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Disconnected from Redis")

    @property
    def client(self) -> redis.Redis:
        """Get the Redis client, raising if not connected."""
        if self._redis is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis

    def _key(self, *parts: str) -> str:
        """Build a namespaced cache key.

        Args:
            *parts: Key parts to join with ':'

        Returns:
            Fully qualified cache key
        """
        return f"{self._key_prefix}:{':'.join(parts)}"

    # =========================================================================
    # Tool Definition Caching
    # =========================================================================

    async def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """Get a cached tool definition.

        Args:
            tool_id: The tool ID

        Returns:
            Tool definition dict or None if not cached
        """
        key = self._key("tool", tool_id)
        data = await self.client.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in cache for key {key}")
        return None

    async def set_tool(
        self,
        tool_id: str,
        definition: Dict[str, Any],
        ttl: int = DEFAULT_TOOL_TTL,
    ) -> None:
        """Cache a tool definition.

        Args:
            tool_id: The tool ID
            definition: Tool definition to cache
            ttl: Time-to-live in seconds
        """
        key = self._key("tool", tool_id)
        await self.client.set(key, json.dumps(definition), ex=ttl)

    async def delete_tool(self, tool_id: str) -> None:
        """Remove a tool definition from cache.

        Args:
            tool_id: The tool ID to remove
        """
        key = self._key("tool", tool_id)
        await self.client.delete(key)

    async def get_tools_by_ids(self, tool_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """Get multiple tool definitions in a single call.

        Args:
            tool_ids: List of tool IDs

        Returns:
            Dict mapping tool_id to definition (or None if not cached)
        """
        if not tool_ids:
            return {}

        keys = [self._key("tool", tid) for tid in tool_ids]
        values = await self.client.mget(keys)

        result: Dict[str, Optional[Dict[str, Any]]] = {}
        for tool_id, value in zip(tool_ids, values):
            if value:
                try:
                    result[tool_id] = json.loads(value)
                except json.JSONDecodeError:
                    result[tool_id] = None
            else:
                result[tool_id] = None

        return result

    # =========================================================================
    # Group Manifest Caching
    # =========================================================================

    async def get_group_manifest(self, group_id: str) -> Optional[List[str]]:
        """Get cached tool IDs for a group.

        Args:
            group_id: The tool group ID

        Returns:
            List of tool IDs or None if not cached
        """
        key = self._key("manifest", "group", group_id)
        data = await self.client.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in cache for key {key}")
        return None

    async def set_group_manifest(
        self,
        group_id: str,
        tool_ids: List[str],
        ttl: int = DEFAULT_MANIFEST_TTL,
    ) -> None:
        """Cache the resolved tool IDs for a group.

        Args:
            group_id: The tool group ID
            tool_ids: List of tool IDs in the group
            ttl: Time-to-live in seconds
        """
        key = self._key("manifest", "group", group_id)
        await self.client.set(key, json.dumps(tool_ids), ex=ttl)

    async def invalidate_group_manifest(self, group_id: str) -> None:
        """Invalidate the cached manifest for a group.

        Args:
            group_id: The tool group ID
        """
        key = self._key("manifest", "group", group_id)
        await self.client.delete(key)

    async def invalidate_all_manifests(self) -> int:
        """Invalidate all group manifests.

        Returns:
            Number of keys deleted
        """
        pattern = self._key("manifest", "group", "*")
        keys = []
        async for key in self.client.scan_iter(pattern):
            keys.append(key)

        if keys:
            return await self.client.delete(*keys)
        return 0

    # =========================================================================
    # Source-Tool Mapping
    # =========================================================================

    async def add_source_tool(self, source_id: str, tool_id: str) -> None:
        """Track that a tool belongs to a source.

        Args:
            source_id: The upstream source ID
            tool_id: The tool ID
        """
        key = self._key("source", source_id, "tools")
        await self.client.sadd(key, tool_id)

    async def remove_source_tool(self, source_id: str, tool_id: str) -> None:
        """Remove a tool from a source's tool set.

        Args:
            source_id: The upstream source ID
            tool_id: The tool ID
        """
        key = self._key("source", source_id, "tools")
        await self.client.srem(key, tool_id)

    async def get_source_tools(self, source_id: str) -> Set[str]:
        """Get all tool IDs for a source.

        Args:
            source_id: The upstream source ID

        Returns:
            Set of tool IDs
        """
        key = self._key("source", source_id, "tools")
        members = await self.client.smembers(key)
        return set(members) if members else set()

    async def clear_source_tools(self, source_id: str) -> None:
        """Clear all tool IDs for a source.

        Args:
            source_id: The upstream source ID
        """
        key = self._key("source", source_id, "tools")
        await self.client.delete(key)

    # =========================================================================
    # Agent Access Cache
    # =========================================================================

    async def get_agent_access_cache(self, claims_hash: str) -> Optional[Set[str]]:
        """Get cached group IDs for agent claims.

        Args:
            claims_hash: Hash of the agent's JWT claims

        Returns:
            Set of allowed group IDs or None if not cached
        """
        key = self._key("access", claims_hash)
        data = await self.client.get(key)
        if data:
            try:
                return set(json.loads(data))
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in cache for key {key}")
        return None

    async def set_agent_access_cache(
        self,
        claims_hash: str,
        group_ids: Set[str],
        ttl: int = DEFAULT_ACCESS_TTL,
    ) -> None:
        """Cache the resolved group IDs for agent claims.

        Args:
            claims_hash: Hash of the agent's JWT claims
            group_ids: Set of allowed group IDs
            ttl: Time-to-live in seconds
        """
        key = self._key("access", claims_hash)
        await self.client.set(key, json.dumps(list(group_ids)), ex=ttl)

    async def invalidate_agent_access_cache(self, claims_hash: str) -> None:
        """Invalidate the access cache for specific claims.

        Args:
            claims_hash: Hash of the agent's JWT claims
        """
        key = self._key("access", claims_hash)
        await self.client.delete(key)

    async def invalidate_all_access_caches(self) -> int:
        """Invalidate all agent access caches.

        Returns:
            Number of keys deleted
        """
        pattern = self._key("access", "*")
        keys = []
        async for key in self.client.scan_iter(pattern):
            keys.append(key)

        if keys:
            return await self.client.delete(*keys)
        return 0

    # =========================================================================
    # Pub/Sub for SSE Notifications
    # =========================================================================

    async def subscribe_to_updates(self, *patterns: str) -> PubSub:
        """Subscribe to update notification channels.

        Args:
            *patterns: Channel patterns to subscribe to
                e.g., "events:group_updated:*", "events:source_updated:*"

        Returns:
            PubSub instance for receiving messages
        """
        pubsub = self.client.pubsub()
        for pattern in patterns:
            await pubsub.psubscribe(self._key("events", pattern))
        return pubsub

    async def publish_update(self, channel: str, message: str) -> int:
        """Publish an update notification.

        Args:
            channel: Channel name (e.g., "group_updated:group123")
            message: Message to publish (typically "REFRESH" or JSON)

        Returns:
            Number of subscribers that received the message
        """
        full_channel = self._key("events", channel)
        return await self.client.publish(full_channel, message)

    async def publish_group_updated(self, group_id: str) -> int:
        """Publish a group update notification.

        Args:
            group_id: The group that was updated

        Returns:
            Number of subscribers notified
        """
        return await self.publish_update(f"group_updated:{group_id}", "REFRESH")

    async def publish_source_updated(self, source_id: str) -> int:
        """Publish a source update notification.

        Args:
            source_id: The source that was updated

        Returns:
            Number of subscribers notified
        """
        return await self.publish_update(f"source_updated:{source_id}", "REFRESH")

    async def publish_tool_updated(self, tool_id: str) -> int:
        """Publish a tool update notification.

        Args:
            tool_id: The tool that was updated

        Returns:
            Number of subscribers notified
        """
        return await self.publish_update(f"tool_updated:{tool_id}", "REFRESH")

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health_check(self) -> bool:
        """Check if Redis is healthy.

        Returns:
            True if Redis responds to ping
        """
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def clear_all(self) -> int:
        """Clear all keys with the configured prefix.

        WARNING: This is destructive and should only be used in testing.

        Returns:
            Number of keys deleted
        """
        pattern = self._key("*")
        keys = []
        async for key in self.client.scan_iter(pattern):
            keys.append(key)

        if keys:
            return await self.client.delete(*keys)
        return 0
