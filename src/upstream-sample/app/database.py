"""
Database configuration for MongoDB persistence.

Uses Motor (async MongoDB driver) for async operations.
"""

import logging
import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# MongoDB connection
_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None

# Default connection settings (dev/docker defaults)
DEFAULT_MONGO_URL = "mongodb://root:password123@mongodb:27017"  # pragma: allowlist secret
DEFAULT_DATABASE = "pizzeria"


def get_mongo_url() -> str:
    """Get MongoDB connection URL from environment or default."""
    return os.getenv("MONGODB_URL", DEFAULT_MONGO_URL)


def get_database_name() -> str:
    """Get database name from environment or default."""
    return os.getenv("MONGODB_DATABASE", DEFAULT_DATABASE)


async def connect_db() -> None:
    """Initialize MongoDB connection."""
    global _client, _db

    mongo_url = get_mongo_url()
    db_name = get_database_name()

    logger.info(f"Connecting to MongoDB: {mongo_url.split('@')[-1]} / {db_name}")

    _client = AsyncIOMotorClient(mongo_url)
    _db = _client[db_name]

    # Verify connection
    try:
        await _client.admin.command("ping")
        logger.info("✅ MongoDB connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB: {e}")
        raise


async def close_db() -> None:
    """Close MongoDB connection."""
    global _client, _db

    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Get the database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _db


def get_collection(name: str) -> AsyncIOMotorCollection:
    """Get a collection by name."""
    return get_database()[name]


# Collection names
MENU_COLLECTION = "menu_items"
ORDERS_COLLECTION = "orders"
COUNTERS_COLLECTION = "counters"


async def get_next_sequence(name: str) -> int:
    """Get the next sequence number for auto-incrementing IDs."""
    counters = get_collection(COUNTERS_COLLECTION)
    result = await counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    return result["seq"]


async def init_indexes() -> None:
    """Create database indexes for better query performance."""
    db = get_database()

    # Menu items indexes
    menu_col = db[MENU_COLLECTION]
    await menu_col.create_index("id", unique=True)
    await menu_col.create_index("category")
    await menu_col.create_index("available")

    # Orders indexes
    orders_col = db[ORDERS_COLLECTION]
    await orders_col.create_index("id", unique=True)
    await orders_col.create_index("customer_id")
    await orders_col.create_index("status")
    await orders_col.create_index("created_at")

    logger.info("✅ Database indexes created")
