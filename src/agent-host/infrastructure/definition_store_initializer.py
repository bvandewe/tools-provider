"""Definition Repository Initializer.

DEPRECATED: Use DatabaseSeederService instead.

This module provides a hosted service that ensures default AgentDefinitions
exist in MongoDB on startup.

Implements HostedService for proper lifecycle management:
- start_async(): Called on application startup to seed defaults
- stop_async(): Called on application shutdown (no-op for this service)
"""

import logging
from typing import TYPE_CHECKING

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from neuroglia.hosting.abstractions import HostedService

from application.settings import app_settings
from domain.models.agent_definition import (
    DEFAULT_REACTIVE_AGENT,
)

if TYPE_CHECKING:
    from neuroglia.hosting.web import WebApplicationBuilder

logger = logging.getLogger(__name__)


class DefinitionSeeder:
    """Simple MongoDB service for seeding default AgentDefinitions.

    DEPRECATED: Use DatabaseSeeder instead.

    This is a lightweight service used only at startup to ensure default
    definitions exist. It bypasses the Neuroglia repository infrastructure
    since HostedServices run before scoped services are available.
    """

    # Collection name must match what Neuroglia's MotorRepository uses:
    # entity_type.__name__.lower() = "agentdefinition"
    COLLECTION_NAME = "agentdefinition"

    # Default definitions seeded on startup
    # Note: Proactive agents require ConversationTemplates (seeded by DatabaseSeeder)
    DEFAULT_DEFINITIONS = [
        DEFAULT_REACTIVE_AGENT,
    ]

    def __init__(self, mongo_url: str, database_name: str) -> None:
        """Initialize the definition seeder.

        Args:
            mongo_url: MongoDB connection URL
            database_name: Database name to use
        """
        self._client = AsyncIOMotorClient(mongo_url)
        self._db = self._client[database_name]
        self._collection: AsyncIOMotorCollection = self._db[self.COLLECTION_NAME]
        logger.debug(f"DefinitionSeeder initialized with database: {database_name}")

    async def ensure_defaults_async(self) -> None:
        """Ensure default definitions exist in MongoDB.

        Uses upsert to avoid duplicates.
        Note: MotorRepository uses `id` field for lookups (not `_id`).
        MongoDB auto-generates `_id` as ObjectId.
        """
        for defn in self.DEFAULT_DEFINITIONS:
            # MotorRepository looks up by `id` field, not `_id`
            existing = await self._collection.find_one({"id": defn.id})
            if existing is None:
                doc = defn.to_dict()
                # Keep `id` field as-is - MotorRepository expects this
                # MongoDB will auto-generate `_id` as ObjectId
                await self._collection.insert_one(doc)
                logger.info(f"Created default definition: {defn.id} ({defn.name})")
            else:
                logger.debug(f"Default definition already exists: {defn.id}")


# Singleton instance for startup seeding
_definition_seeder: DefinitionSeeder | None = None


def get_definition_seeder() -> DefinitionSeeder:
    """Get the singleton definition seeder.

    Returns:
        The DefinitionSeeder singleton

    Raises:
        RuntimeError: If seeder not initialized
    """
    if _definition_seeder is None:
        raise RuntimeError("DefinitionSeeder not initialized.")
    return _definition_seeder


class DefinitionRepositoryInitializer(HostedService):
    """Hosted service that initializes default definitions on startup.

    Implements HostedService for automatic lifecycle management:
    - start_async(): Called on application startup to seed defaults
    - stop_async(): Called on application shutdown (cleanup if needed)

    This service ensures that default AgentDefinitions exist in MongoDB
    so users can immediately start conversations.
    """

    def __init__(self) -> None:
        """Initialize the definition repository initializer."""
        self._initialized = False

    # =========================================================================
    # HostedService Lifecycle Methods
    # =========================================================================

    async def start_async(self) -> None:
        """Start the service by ensuring default definitions exist.

        Called automatically by the Neuroglia host during application startup.
        Creates default definitions if they don't exist.
        """
        try:
            seeder = get_definition_seeder()
            await seeder.ensure_defaults_async()
            self._initialized = True
            logger.info("✅ DefinitionRepositoryInitializer started - default definitions ensured")
        except Exception as e:
            logger.error(f"❌ DefinitionRepositoryInitializer failed: {e}")
            # Don't raise - the app can still function, just without defaults

    async def stop_async(self) -> None:
        """Stop the service.

        Called automatically by the Neuroglia host during application shutdown.
        No cleanup needed for this service.
        """
        logger.info("✅ DefinitionRepositoryInitializer stopped")

    # =========================================================================
    # Static Configuration Method
    # =========================================================================

    @staticmethod
    def configure(builder: "WebApplicationBuilder") -> "WebApplicationBuilder":
        """Configure the definition repository initializer as a hosted service.

        This method follows the Neuroglia pattern for service configuration,
        registering DefinitionRepositoryInitializer as a HostedService for automatic
        lifecycle management.

        Note: Creates a dedicated DefinitionSeeder instance for startup
        seeding since the DI-registered repository is scoped and not available
        during HostedService startup.

        Args:
            builder: The WebApplicationBuilder to configure

        Returns:
            The builder instance for fluent chaining
        """
        global _definition_seeder

        logger.info("🔧 Configuring DefinitionRepositoryInitializer...")

        # Create a dedicated seeder instance for startup
        # Key is "mongo" in connection_strings (matching docker-compose and settings)
        mongo_url = app_settings.connection_strings.get("mongo", "mongodb://localhost:27017")
        _definition_seeder = DefinitionSeeder(
            mongo_url=mongo_url,
            database_name=app_settings.database_name,
        )

        initializer = DefinitionRepositoryInitializer()

        # Register as HostedService for lifecycle management (start_async/stop_async)
        builder.services.add_singleton(HostedService, singleton=initializer)

        logger.info("✅ DefinitionRepositoryInitializer configured")
        return builder
