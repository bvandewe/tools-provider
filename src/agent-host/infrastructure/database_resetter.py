"""Database Resetter for clearing and re-seeding data.

This module provides a service to reset MongoDB and re-seed from YAML files
via the DatabaseSeeder.

This is a destructive operation intended for development/testing use only.

Architecture:
- MongoDB: Primary data store for all aggregates and DTOs
- Re-seeding: DatabaseSeeder handles creating fresh aggregates from YAML
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from neuroglia.dependency_injection import ServiceProviderBase

from application.settings import app_settings
from infrastructure.database_seeder import get_database_seeder

if TYPE_CHECKING:
    from neuroglia.hosting.web import WebApplicationBuilder

logger = logging.getLogger(__name__)


@dataclass
class ResetDatabaseResult:
    """Result of the database reset operation."""

    cleared_write_model: bool
    """Whether aggregate documents were cleared."""

    cleared_read_model: bool
    """Whether DTO collections were cleared."""

    seeded: dict[str, int] = field(default_factory=dict)
    """Counts of entities seeded after reset."""

    message: str = ""
    """Human-readable summary message."""

    reset_by: str | None = None
    """Username of the admin who triggered the reset."""


class DatabaseResetter:
    """Service to reset all application data.

    Clears MongoDB collections and re-seeds from YAML files.

    MongoDB Collections (matches Neuroglia's naming convention):
    - conversations (Conversation aggregates)
    - agent_definitions (AgentDefinition aggregates)
    - conversation_templates (ConversationTemplate aggregates)
    - conversation_dto (ConversationDto read model)
    - agent_definition_dto (AgentDefinitionDto read model)
    - conversation_template_dto (ConversationTemplateDto read model)
    """

    # MongoDB collections to clear (matches MotorRepository.configure() in main.py)
    MONGO_COLLECTIONS = [
        # Aggregates
        "conversations",
        "agent_definitions",
        "conversation_templates",
        # DTOs (read model)
        "conversation_dto",
        "agent_definition_dto",
        "conversation_template_dto",
    ]

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        mongo_url: str,
        database_name: str,
    ) -> None:
        """Initialize the database resetter.

        Args:
            service_provider: Service provider for accessing DatabaseSeeder
            mongo_url: MongoDB connection URL
            database_name: Database name for MongoDB
        """
        self._service_provider = service_provider
        self._mongo_url = mongo_url
        self._database_name = database_name

        # MongoDB client (created on demand)
        self._mongo_client: AsyncIOMotorClient | None = None
        self._mongo_db: AsyncIOMotorDatabase | None = None

        logger.debug(f"DatabaseResetter initialized for database: {database_name}")

    def _get_mongo_db(self) -> AsyncIOMotorDatabase:
        """Get or create MongoDB database connection.

        Returns:
            AsyncIOMotorDatabase instance
        """
        if self._mongo_client is None:
            self._mongo_client = AsyncIOMotorClient(self._mongo_url)
            self._mongo_db = self._mongo_client[self._database_name]
        assert self._mongo_db is not None  # Guaranteed by the above initialization
        return self._mongo_db

    async def reset_all_async(self, reset_by: str | None = None) -> ResetDatabaseResult:
        """Reset all data and re-seed from YAML.

        This operation:
        1. Clears all MongoDB collections
        2. Re-seeds from YAML files via DatabaseSeeder

        Args:
            reset_by: Username of admin who triggered the reset

        Returns:
            ResetDatabaseResult with operation summary
        """
        logger.warning(f"🗑️ Starting database reset (requested by: {reset_by})")

        cleared_read_model = False
        cleared_write_model = False
        seeded: dict[str, int] = {}
        messages: list[str] = []

        # Step 1: Clear all MongoDB collections
        try:
            await self._clear_mongodb_async()
            cleared_read_model = True
            cleared_write_model = True  # Both are in MongoDB now
            messages.append("MongoDB collections cleared")
            logger.info("✅ MongoDB cleared")
        except Exception as e:
            logger.error(f"❌ Failed to clear MongoDB: {e}")
            messages.append(f"MongoDB clear failed: {str(e)}")

        # Step 2: Re-seed from YAML via DatabaseSeeder
        try:
            seeder = get_database_seeder()
            seeded = await seeder.seed_all_async()
            messages.append(f"Seeded: {seeded}")
            logger.info(f"✅ Database re-seeded: {seeded}")
        except Exception as e:
            logger.error(f"❌ Failed to re-seed database: {e}")
            messages.append(f"Seeding failed: {str(e)}")

        return ResetDatabaseResult(
            cleared_write_model=cleared_write_model,
            cleared_read_model=cleared_read_model,
            seeded=seeded,
            message=" | ".join(messages),
            reset_by=reset_by,
        )

    async def _clear_mongodb_async(self) -> None:
        """Clear all MongoDB collections.

        Drops each collection entirely, which is faster than delete_many({}).
        Collections will be auto-recreated when seeder runs.
        """
        db = self._get_mongo_db()

        for collection_name in self.MONGO_COLLECTIONS:
            try:
                await db.drop_collection(collection_name)
                logger.debug(f"Dropped MongoDB collection: {collection_name}")
            except Exception as e:
                logger.warning(f"Could not drop collection {collection_name}: {e}")
                # Continue with other collections

    @staticmethod
    def configure(builder: "WebApplicationBuilder") -> "WebApplicationBuilder":
        """Configure the DatabaseResetter as a singleton service.

        Note: This uses a deferred factory because DatabaseResetter needs
        access to the service provider. The service is registered as scoped
        to work with Neuroglia's Mediator handler resolution.

        Args:
            builder: The WebApplicationBuilder to configure

        Returns:
            The builder instance for fluent chaining
        """
        logger.info("🔧 Configuring DatabaseResetter...")

        # Get MongoDB URL from connection strings
        mongo_url = app_settings.connection_strings.get("mongo", "")
        if not mongo_url:
            raise ValueError("MongoDB connection string not configured")

        def create_resetter(sp: ServiceProviderBase) -> DatabaseResetter:
            """Factory to create DatabaseResetter with service provider access."""
            resetter = DatabaseResetter(
                service_provider=sp,
                mongo_url=mongo_url,
                database_name=app_settings.database_name,
            )
            set_database_resetter(resetter)
            return resetter

        # Register as scoped - Neuroglia's Mediator resolves handlers in scoped context
        builder.services.add_scoped(DatabaseResetter, implementation_factory=create_resetter)

        logger.info("✅ DatabaseResetter configured")
        return builder


# Singleton accessor (optional, for direct access outside DI)
_database_resetter: DatabaseResetter | None = None


def get_database_resetter() -> DatabaseResetter:
    """Get the singleton database resetter.

    Returns:
        The DatabaseResetter singleton

    Raises:
        RuntimeError: If resetter not initialized
    """
    if _database_resetter is None:
        raise RuntimeError("DatabaseResetter not initialized. Use DI container instead.")
    return _database_resetter


def set_database_resetter(resetter: DatabaseResetter) -> None:
    """Set the singleton database resetter.

    Args:
        resetter: The DatabaseResetter instance to set as singleton
    """
    global _database_resetter
    _database_resetter = resetter
