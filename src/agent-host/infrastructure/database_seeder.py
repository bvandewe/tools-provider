"""Database Seeder for YAML-based initialization.

This module provides a unified HostedService that seeds both AgentDefinitions
and ConversationTemplates from YAML files at application startup.

Replaces the older DefinitionRepositoryInitializer with a more comprehensive
approach that handles multiple entity types from external YAML sources.

Seeding Strategy: "Seed-only"
- Creates entities that don't exist (by ID)
- Does NOT update existing entities
- Manual database updates required for changes
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from neuroglia.hosting.abstractions import HostedService

from application.settings import app_settings
from domain.models.agent_definition import AgentDefinition
from domain.models.conversation_template import ConversationTemplate
from infrastructure.skill_loader import SkillLoader, set_skill_loader

if TYPE_CHECKING:
    from neuroglia.hosting.web import WebApplicationBuilder

logger = logging.getLogger(__name__)


class DatabaseSeeder:
    """MongoDB seeder for AgentDefinitions and ConversationTemplates.

    This service seeds the database from YAML files at startup.
    It uses direct MongoDB access since HostedServices run before
    scoped DI services are available.
    """

    # Collection names (must match Neuroglia's MotorRepository naming)
    DEFINITIONS_COLLECTION = "agentdefinition"
    TEMPLATES_COLLECTION = "conversationtemplate"

    def __init__(
        self,
        mongo_url: str,
        database_name: str,
        agents_dir: str | Path,
        templates_dir: str | Path,
        skills_dir: str | Path,
    ) -> None:
        """Initialize the database seeder.

        Args:
            mongo_url: MongoDB connection URL
            database_name: Database name to use
            agents_dir: Directory containing agent definition YAML files
            templates_dir: Directory containing template YAML files
            skills_dir: Directory containing skill YAML files
        """
        self._client = AsyncIOMotorClient(mongo_url)
        self._db = self._client[database_name]
        self._definitions_collection: AsyncIOMotorCollection = self._db[self.DEFINITIONS_COLLECTION]
        self._templates_collection: AsyncIOMotorCollection = self._db[self.TEMPLATES_COLLECTION]
        self._agents_dir = Path(agents_dir)
        self._templates_dir = Path(templates_dir)
        self._skills_dir = Path(skills_dir)

        # Create and register skill loader
        self._skill_loader = SkillLoader(self._skills_dir)
        set_skill_loader(self._skill_loader)

        logger.debug(f"DatabaseSeeder initialized with database: {database_name}")

    async def seed_all_async(self) -> dict[str, int]:
        """Seed all entity types from YAML files.

        Returns:
            Dictionary with counts for each entity type seeded
        """
        results = {
            "skills": 0,
            "definitions": 0,
            "templates": 0,
        }

        # Load skills first (needed for template validation)
        results["skills"] = await self._skill_loader.load_async()

        # Seed definitions
        results["definitions"] = await self._seed_definitions_async()

        # Seed templates
        results["templates"] = await self._seed_templates_async()

        return results

    async def _seed_definitions_async(self) -> int:
        """Seed AgentDefinitions from YAML files.

        Returns:
            Number of definitions seeded
        """
        if not self._agents_dir.exists():
            logger.warning(f"Agents directory does not exist: {self._agents_dir}")
            return 0

        yaml_files = list(self._agents_dir.glob("*.yaml")) + list(self._agents_dir.glob("*.yml"))
        seeded_count = 0

        for yaml_file in yaml_files:
            try:
                seeded = await self._seed_definition_file_async(yaml_file)
                seeded_count += seeded
            except Exception as e:
                logger.error(f"Error seeding definition from {yaml_file}: {e}")

        logger.info(f"Seeded {seeded_count} definitions from {len(yaml_files)} files")
        return seeded_count

    async def _seed_definition_file_async(self, yaml_file: Path) -> int:
        """Seed a single definition YAML file.

        Args:
            yaml_file: Path to the YAML file

        Returns:
            1 if seeded, 0 if skipped
        """
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or not isinstance(data, dict):
            logger.warning(f"Invalid definition YAML: {yaml_file}")
            return 0

        definition_id = data.get("id")
        if not definition_id:
            logger.warning(f"Definition without 'id' in {yaml_file}")
            return 0

        # Check if already exists
        existing = await self._definitions_collection.find_one({"id": definition_id})
        if existing is not None:
            logger.debug(f"Definition already exists, skipping: {definition_id}")
            return 0

        # Create and insert
        definition = AgentDefinition.from_dict(data)
        doc = definition.to_dict()
        await self._definitions_collection.insert_one(doc)
        logger.info(f"Seeded definition: {definition_id} ({definition.name})")
        return 1

    async def _seed_templates_async(self) -> int:
        """Seed ConversationTemplates from YAML files.

        Returns:
            Number of templates seeded
        """
        if not self._templates_dir.exists():
            logger.warning(f"Templates directory does not exist: {self._templates_dir}")
            return 0

        yaml_files = list(self._templates_dir.glob("*.yaml")) + list(self._templates_dir.glob("*.yml"))
        seeded_count = 0

        for yaml_file in yaml_files:
            try:
                seeded = await self._seed_template_file_async(yaml_file)
                seeded_count += seeded
            except Exception as e:
                logger.error(f"Error seeding template from {yaml_file}: {e}")

        logger.info(f"Seeded {seeded_count} templates from {len(yaml_files)} files")
        return seeded_count

    async def _seed_template_file_async(self, yaml_file: Path) -> int:
        """Seed a single template YAML file.

        Args:
            yaml_file: Path to the YAML file

        Returns:
            1 if seeded, 0 if skipped
        """
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data or not isinstance(data, dict):
            logger.warning(f"Invalid template YAML: {yaml_file}")
            return 0

        template_id = data.get("id")
        if not template_id:
            logger.warning(f"Template without 'id' in {yaml_file}")
            return 0

        # Check if already exists
        existing = await self._templates_collection.find_one({"id": template_id})
        if existing is not None:
            logger.debug(f"Template already exists, skipping: {template_id}")
            return 0

        # Create and insert
        template = ConversationTemplate.from_dict(data)
        doc = template.to_dict()
        await self._templates_collection.insert_one(doc)
        logger.info(f"Seeded template: {template_id} ({template.name})")
        return 1


# =============================================================================
# Singleton for Startup Access
# =============================================================================

_database_seeder: DatabaseSeeder | None = None


def get_database_seeder() -> DatabaseSeeder:
    """Get the singleton database seeder.

    Returns:
        The DatabaseSeeder singleton

    Raises:
        RuntimeError: If seeder not initialized
    """
    if _database_seeder is None:
        raise RuntimeError("DatabaseSeeder not initialized.")
    return _database_seeder


class DatabaseSeederService(HostedService):
    """Hosted service that seeds the database on startup.

    Implements HostedService for automatic lifecycle management:
    - start_async(): Called on application startup to seed from YAML
    - stop_async(): Called on application shutdown (cleanup if needed)
    """

    def __init__(self) -> None:
        """Initialize the database seeder service."""
        self._initialized = False
        self._seed_results: dict[str, int] = {}

    @property
    def seed_results(self) -> dict[str, int]:
        """Get the results from the last seeding operation."""
        return self._seed_results

    async def start_async(self) -> None:
        """Start the service by seeding the database.

        Called automatically by the Neuroglia host during application startup.
        Seeds definitions and templates from YAML files.
        """
        try:
            seeder = get_database_seeder()
            self._seed_results = await seeder.seed_all_async()
            self._initialized = True

            logger.info(
                f"✅ DatabaseSeederService started - "
                f"skills: {self._seed_results.get('skills', 0)}, "
                f"definitions: {self._seed_results.get('definitions', 0)}, "
                f"templates: {self._seed_results.get('templates', 0)}"
            )
        except Exception as e:
            logger.error(f"❌ DatabaseSeederService failed: {e}")
            # Don't raise - the app can still function

    async def stop_async(self) -> None:
        """Stop the service.

        Called automatically by the Neuroglia host during application shutdown.
        """
        logger.info("✅ DatabaseSeederService stopped")

    @staticmethod
    def configure(builder: "WebApplicationBuilder") -> "WebApplicationBuilder":
        """Configure the database seeder as a hosted service.

        Args:
            builder: The WebApplicationBuilder to configure

        Returns:
            The builder instance for fluent chaining
        """
        global _database_seeder

        logger.info("🔧 Configuring DatabaseSeederService...")

        # Get MongoDB connection info
        mongo_url = app_settings.connection_strings.get("mongo", "mongodb://localhost:27017")

        # Determine data directories (relative to application root)
        # These are typically in src/agent-host/data/
        import os

        base_dir = Path(os.path.dirname(os.path.dirname(__file__)))  # agent-host root
        data_dir = base_dir / "data"

        _database_seeder = DatabaseSeeder(
            mongo_url=mongo_url,
            database_name=app_settings.database_name,
            agents_dir=data_dir / "agents",
            templates_dir=data_dir / "templates",
            skills_dir=data_dir / "skills" if (data_dir / "skills").exists() else data_dir / "blueprints",
        )

        service = DatabaseSeederService()
        builder.services.add_singleton(HostedService, singleton=service)

        logger.info("✅ DatabaseSeederService configured")
        return builder
