"""Application Settings Service for MongoDB storage and retrieval."""

import logging
from datetime import UTC, datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

from application.settings import app_settings
from integration.models.app_settings_dto import AppSettingsDto

logger = logging.getLogger(__name__)

# Singleton instance
_settings_service: Optional["AppSettingsService"] = None


class AppSettingsService:
    """Service for managing application settings in MongoDB.

    Settings are stored as a singleton document with subsections for LLM, Agent, and UI.
    """

    SETTINGS_ID = "app_settings"
    COLLECTION_NAME = "app_settings"
    DATABASE_NAME = "agent_host"

    def __init__(self, mongo_url: str) -> None:
        """Initialize the settings service.

        Args:
            mongo_url: MongoDB connection URL
        """
        self._client = AsyncIOMotorClient(mongo_url)
        self._db = self._client[self.DATABASE_NAME]
        self._collection: AsyncIOMotorCollection = self._db[self.COLLECTION_NAME]
        self._cached_settings: AppSettingsDto | None = None
        logger.info(f"AppSettingsService initialized with database: {self.DATABASE_NAME}")

    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get the MongoDB collection."""
        return self._collection

    async def get_settings_async(self, use_cache: bool = True) -> AppSettingsDto | None:
        """Get the current application settings from MongoDB.

        Args:
            use_cache: Whether to use cached settings if available

        Returns:
            AppSettingsDto if found, None otherwise
        """
        if use_cache and self._cached_settings is not None:
            return self._cached_settings

        try:
            doc = await self._collection.find_one({"_id": self.SETTINGS_ID})
            if doc:
                # Convert _id to id for DTO
                doc["id"] = doc.pop("_id")
                self._cached_settings = AppSettingsDto.from_dict(doc)
                logger.debug("Loaded settings from MongoDB")
                return self._cached_settings
            logger.debug("No settings found in MongoDB")
            return None
        except Exception as e:
            logger.error(f"Failed to load settings from MongoDB: {e}")
            return None

    async def save_settings_async(self, settings: AppSettingsDto, updated_by: str) -> AppSettingsDto:
        """Save application settings to MongoDB.

        Uses upsert to create or update the singleton settings document.

        Args:
            settings: The settings to save
            updated_by: Username/ID of the user making the change

        Returns:
            The saved settings
        """
        settings.updated_at = datetime.now(UTC)
        settings.updated_by = updated_by
        settings.id = self.SETTINGS_ID  # Ensure correct ID

        doc = settings.to_dict()
        # Use _id for MongoDB - always use SETTINGS_ID to ensure consistency
        doc.pop("id", None)
        doc["_id"] = self.SETTINGS_ID

        try:
            await self._collection.replace_one({"_id": self.SETTINGS_ID}, doc, upsert=True)
            # Clear cache to force reload
            self._cached_settings = settings
            logger.info(f"Settings saved by {updated_by}")
            return settings
        except Exception as e:
            logger.error(f"Failed to save settings to MongoDB: {e}")
            raise

    async def delete_settings_async(self) -> bool:
        """Delete the settings document (reset to defaults).

        Returns:
            True if deleted, False if not found
        """
        try:
            result = await self._collection.delete_one({"_id": self.SETTINGS_ID})
            self._cached_settings = None
            if result.deleted_count > 0:
                logger.info("Settings deleted (reset to defaults)")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete settings: {e}")
            raise

    def clear_cache(self) -> None:
        """Clear the cached settings."""
        self._cached_settings = None


def get_settings_service() -> AppSettingsService:
    """Get the singleton settings service instance.

    Returns:
        AppSettingsService instance
    """
    global _settings_service
    if _settings_service is None:
        mongo_url = app_settings.connection_strings.get("mongo", "mongodb://localhost:27017")
        _settings_service = AppSettingsService(mongo_url)
    return _settings_service


def set_settings_service(service: AppSettingsService) -> None:
    """Set the singleton settings service instance (for testing)."""
    global _settings_service
    _settings_service = service
