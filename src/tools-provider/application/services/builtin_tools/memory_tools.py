"""Memory tools for persistent key-value storage.

Tools for agent memory:
- memory_store: Store key-value pairs with optional TTL
- memory_retrieve: Retrieve stored values
"""

import json
import logging
import os
import re
import tempfile
from datetime import UTC, datetime, timedelta
from typing import Any

from application.settings import Settings

from .base import BuiltinToolResult, UserContext

logger = logging.getLogger(__name__)

# Module-level Redis connection cache
_redis_memory: Any = None


async def _get_redis_memory() -> Any:
    """Get or create Redis connection for agent memory."""
    global _redis_memory

    if _redis_memory is not None:
        return _redis_memory

    try:
        import redis.asyncio as redis_lib  # Optional dependency

        settings = Settings()
        if not settings.redis_enabled:
            logger.debug("Redis disabled, using file-based memory")
            return None

        _redis_memory = redis_lib.from_url(settings.redis_memory_url, decode_responses=True)
        await _redis_memory.ping()
        logger.info(f"Redis memory connected: {settings.redis_memory_url}")
        return _redis_memory

    except Exception as e:
        logger.warning(f"Redis memory unavailable, using file fallback: {e}")
        _redis_memory = None
        return None


def _get_memory_key(key: str, user_context: UserContext | None) -> str:
    """Get the full Redis key with prefix and user scoping."""
    settings = Settings()
    prefix = settings.redis_memory_key_prefix

    if user_context and user_context.user_id:
        return f"{prefix}{user_context.user_id}:{key}"
    else:
        logger.warning("Memory operation without user context - using anonymous namespace")
        return f"{prefix}anonymous:{key}"


async def execute_memory_store(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the memory_store tool using Redis with file fallback."""
    key = arguments.get("key", "")
    value = arguments.get("value", "")
    ttl_days = min(arguments.get("ttl_days", 30), 365)

    if not key:
        return BuiltinToolResult(success=False, error="Key is required")
    if not value:
        return BuiltinToolResult(success=False, error="Value is required")

    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
        return BuiltinToolResult(
            success=False,
            error="Key must be alphanumeric with underscores, starting with a letter or underscore",
        )

    logger.info(f"Memory store: {key}")

    expiry_seconds = ttl_days * 86400 if ttl_days > 0 else None
    expiry_iso = (datetime.now(UTC) + timedelta(days=ttl_days)).isoformat() if ttl_days > 0 else None
    stored_at = datetime.now(UTC).isoformat()

    try:
        redis_client = await _get_redis_memory()

        if redis_client:
            redis_key = _get_memory_key(key, user_context)
            data = json.dumps({"value": value, "stored_at": stored_at, "expires_at": expiry_iso})

            if expiry_seconds:
                await redis_client.setex(redis_key, expiry_seconds, data)
            else:
                await redis_client.set(redis_key, data)

            return BuiltinToolResult(
                success=True,
                result={"key": key, "stored": True, "expires_at": expiry_iso, "storage": "redis"},
            )

        else:
            return await _memory_store_file(key, value, stored_at, expiry_iso, user_context)

    except Exception as e:
        logger.exception(f"Memory store failed: {e}")
        return BuiltinToolResult(success=False, error=f"Store failed: {str(e)}")


async def _memory_store_file(key: str, value: str, stored_at: str, expires_at: str | None, user_context: UserContext | None) -> BuiltinToolResult:
    """File-based memory storage fallback."""
    user_id = user_context.user_id if user_context else "anonymous"
    memory_dir = os.path.join(tempfile.gettempdir(), "agent_memory", user_id)
    os.makedirs(memory_dir, exist_ok=True)
    memory_file = os.path.join(memory_dir, "memory.json")

    memory = {}
    if os.path.exists(memory_file):
        with open(memory_file) as f:
            memory = json.load(f)

    memory[key] = {"value": value, "stored_at": stored_at, "expires_at": expires_at}

    with open(memory_file, "w") as f:
        json.dump(memory, f, indent=2)

    return BuiltinToolResult(
        success=True,
        result={"key": key, "stored": True, "expires_at": expires_at, "storage": "file"},
    )


async def execute_memory_retrieve(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute the memory_retrieve tool using Redis with file fallback."""
    key = arguments.get("key")
    default = arguments.get("default")

    logger.info(f"Memory retrieve: {key or 'all keys'}")

    try:
        redis_client = await _get_redis_memory()

        if redis_client:
            return await _memory_retrieve_redis(redis_client, key, default, user_context)
        else:
            return await _memory_retrieve_file(key, default, user_context)

    except Exception as e:
        logger.exception(f"Memory retrieve failed: {e}")
        return BuiltinToolResult(success=False, error=f"Retrieve failed: {str(e)}")


async def _memory_retrieve_redis(redis_client: Any, key: str | None, default: Any, user_context: UserContext | None) -> BuiltinToolResult:
    """Retrieve from Redis memory."""
    settings = Settings()
    prefix = settings.redis_memory_key_prefix
    user_id = user_context.user_id if user_context else "anonymous"
    user_prefix = f"{prefix}{user_id}:"

    if key is None:
        pattern = f"{user_prefix}*"
        keys = []
        async for k in redis_client.scan_iter(match=pattern):
            keys.append(k.replace(user_prefix, "", 1))

        return BuiltinToolResult(
            success=True,
            result={"keys": keys, "count": len(keys), "storage": "redis"},
        )

    redis_key = _get_memory_key(key, user_context)
    data = await redis_client.get(redis_key)

    if data:
        parsed = json.loads(data)
        return BuiltinToolResult(
            success=True,
            result={"key": key, "value": parsed["value"], "stored_at": parsed["stored_at"], "storage": "redis"},
        )
    elif default is not None:
        return BuiltinToolResult(
            success=True,
            result={"key": key, "value": default, "is_default": True},
        )
    else:
        return BuiltinToolResult(success=False, error=f"Key not found: {key}")


async def _memory_retrieve_file(key: str | None, default: Any, user_context: UserContext | None) -> BuiltinToolResult:
    """File-based memory retrieval fallback."""
    user_id = user_context.user_id if user_context else "anonymous"
    memory_dir = os.path.join(tempfile.gettempdir(), "agent_memory", user_id)
    memory_file = os.path.join(memory_dir, "memory.json")

    memory = {}
    if os.path.exists(memory_file):
        with open(memory_file) as f:
            memory = json.load(f)

    now = datetime.now(UTC)
    memory = {k: v for k, v in memory.items() if v.get("expires_at") is None or datetime.fromisoformat(v["expires_at"]) > now}

    if key is None:
        return BuiltinToolResult(
            success=True,
            result={"keys": list(memory.keys()), "count": len(memory), "storage": "file"},
        )

    if key in memory:
        return BuiltinToolResult(
            success=True,
            result={"key": key, "value": memory[key]["value"], "stored_at": memory[key]["stored_at"], "storage": "file"},
        )
    elif default is not None:
        return BuiltinToolResult(
            success=True,
            result={"key": key, "value": default, "is_default": True},
        )
    else:
        return BuiltinToolResult(success=False, error=f"Key not found: {key}")
