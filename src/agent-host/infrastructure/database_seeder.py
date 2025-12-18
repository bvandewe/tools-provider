"""Database Seeder for YAML-based initialization.

This module provides a unified HostedService that seeds both AgentDefinitions
and ConversationTemplates from YAML files at application startup.

Replaces the older DefinitionRepositoryInitializer with a more comprehensive
approach that handles multiple entity types from external YAML sources.

Seeding Strategy: "Seed-only" via MotorRepository
- Creates aggregates that don't exist (by ID) in MongoDB
- Does NOT update existing aggregates
- Manual updates required for changes

IMPORTANT: This seeder uses Repository[T, str] pattern:
- Aggregates are created and saved via Repository[AgentDefinition, str]
- Domain events are published via CloudEventPublisher
- All data is persisted to MongoDB via MotorRepository
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from neuroglia.data.infrastructure.abstractions import Repository
from neuroglia.dependency_injection import ServiceProviderBase
from neuroglia.hosting.abstractions import HostedService

from domain.entities import AgentDefinition, ConversationTemplate
from domain.models import ConversationItem
from infrastructure.skill_loader import SkillLoader, set_skill_loader

if TYPE_CHECKING:
    from neuroglia.hosting.web import WebApplicationBuilder

logger = logging.getLogger(__name__)


class DatabaseSeeder:
    """Seeder for AgentDefinitions and ConversationTemplates from YAML.

    This service seeds aggregates from YAML files at startup:
    - Creates aggregates via Repository[T, str] (MotorRepository)
    - Domain events are published via CloudEventPublisher for external consumers
    - All data persisted to MongoDB
    """

    def __init__(
        self,
        service_provider: ServiceProviderBase,
        agents_dir: str | Path,
        templates_dir: str | Path,
        skills_dir: str | Path,
    ) -> None:
        """Initialize the database seeder.

        Args:
            service_provider: The root service provider for creating scopes
            agents_dir: Directory containing agent definition YAML files
            templates_dir: Directory containing template YAML files
            skills_dir: Directory containing skill YAML files
        """
        self._service_provider = service_provider
        self._agents_dir = Path(agents_dir)
        self._templates_dir = Path(templates_dir)
        self._skills_dir = Path(skills_dir)

        # Create and register skill loader
        self._skill_loader = SkillLoader(self._skills_dir)
        set_skill_loader(self._skill_loader)

        logger.debug("DatabaseSeeder initialized with Event Sourcing pattern")

    async def seed_all_async(self) -> dict[str, int]:
        """Seed all entity types from YAML files.

        Uses a scoped service provider to access repositories.

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

        # Create a scope for repository access
        async with self._service_provider.create_async_scope() as scoped_provider:
            # Get repositories from scope
            definition_repo: Repository[AgentDefinition, str] = scoped_provider.get_required_service(Repository[AgentDefinition, str])
            template_repo: Repository[ConversationTemplate, str] = scoped_provider.get_required_service(Repository[ConversationTemplate, str])

            # Seed definitions
            results["definitions"] = await self._seed_definitions_async(definition_repo)

            # Seed templates
            results["templates"] = await self._seed_templates_async(template_repo)

        return results

    async def _seed_definitions_async(
        self,
        repository: Repository[AgentDefinition, str],
    ) -> int:
        """Seed AgentDefinitions from YAML files.

        Args:
            repository: The AgentDefinition aggregate repository (WriteModel)

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
                seeded = await self._seed_definition_file_async(yaml_file, repository)
                seeded_count += seeded
            except Exception as e:
                logger.error(f"Error seeding definition from {yaml_file}: {e}")
                import traceback

                logger.debug(traceback.format_exc())

        logger.info(f"Seeded {seeded_count} definitions from {len(yaml_files)} files")
        return seeded_count

    async def _seed_definition_file_async(
        self,
        yaml_file: Path,
        repository: Repository[AgentDefinition, str],
    ) -> int:
        """Seed a single definition YAML file.

        Args:
            yaml_file: Path to the YAML file
            repository: The AgentDefinition aggregate repository

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

        # Check WriteModel for existing aggregate
        existing = await repository.get_async(definition_id)
        if existing is not None:
            logger.debug(f"Definition already exists in WriteModel, skipping: {definition_id}")
            return 0

        # Create aggregate from YAML data
        aggregate = self._create_definition_aggregate(data)

        # Save via repository (triggers events -> projections)
        await repository.add_async(aggregate)
        logger.info(f"Seeded definition: {definition_id} ({aggregate.state.name})")
        return 1

    def _create_definition_aggregate(self, data: dict[str, Any]) -> AgentDefinition:
        """Create an AgentDefinition aggregate from YAML data.

        Args:
            data: Dictionary parsed from YAML file

        Returns:
            AgentDefinition aggregate instance
        """
        return AgentDefinition(
            definition_id=data.get("id"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            system_prompt=data.get("system_prompt", ""),
            icon=data.get("icon"),
            tools=data.get("tools", []),
            model=data.get("model"),
            conversation_template_id=data.get("conversation_template_id"),
            is_public=data.get("is_public", True),
            required_roles=data.get("required_roles", []),
            required_scopes=data.get("required_scopes", []),
            allowed_users=data.get("allowed_users"),
            owner_user_id=data.get("owner_user_id"),
            created_by=data.get("created_by", "seeder"),
        )

    async def _seed_templates_async(
        self,
        repository: Repository[ConversationTemplate, str],
    ) -> int:
        """Seed ConversationTemplates from YAML files.

        Args:
            repository: The ConversationTemplate aggregate repository (WriteModel)

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
                seeded = await self._seed_template_file_async(yaml_file, repository)
                seeded_count += seeded
            except Exception as e:
                logger.error(f"Error seeding template from {yaml_file}: {e}")
                import traceback

                logger.debug(traceback.format_exc())

        logger.info(f"Seeded {seeded_count} templates from {len(yaml_files)} files")
        return seeded_count

    async def _seed_template_file_async(
        self,
        yaml_file: Path,
        repository: Repository[ConversationTemplate, str],
    ) -> int:
        """Seed a single template YAML file.

        Args:
            yaml_file: Path to the YAML file
            repository: The ConversationTemplate aggregate repository

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

        # Check WriteModel for existing aggregate
        existing = await repository.get_async(template_id)
        if existing is not None:
            logger.debug(f"Template already exists in WriteModel, skipping: {template_id}")
            return 0

        # Create aggregate from YAML data
        aggregate = self._create_template_aggregate(data)

        # Save via repository (triggers events -> projections)
        await repository.add_async(aggregate)
        logger.info(f"Seeded template: {template_id} ({aggregate.state.name})")
        return 1

    def _create_template_aggregate(self, data: dict[str, Any]) -> ConversationTemplate:
        """Create a ConversationTemplate aggregate from YAML data.

        Args:
            data: Dictionary parsed from YAML file

        Returns:
            ConversationTemplate aggregate instance
        """
        # Parse items if present
        items_data = data.get("items", [])
        items = [ConversationItem.from_dict(item) for item in items_data]

        return ConversationTemplate(
            template_id=data.get("id"),
            name=data.get("name", ""),
            description=data.get("description"),
            agent_starts_first=data.get("agent_starts_first", False),
            allow_agent_switching=data.get("allow_agent_switching", False),
            allow_navigation=data.get("allow_navigation", False),
            allow_backward_navigation=data.get("allow_backward_navigation", False),
            enable_chat_input_initially=data.get("enable_chat_input_initially", True),
            continue_after_completion=data.get("continue_after_completion", False),
            min_duration_seconds=data.get("min_duration_seconds"),
            max_duration_seconds=data.get("max_duration_seconds"),
            shuffle_items=data.get("shuffle_items", False),
            display_progress_indicator=data.get("display_progress_indicator", True),
            display_item_score=data.get("display_item_score", False),
            display_item_title=data.get("display_item_title", True),
            display_final_score_report=data.get("display_final_score_report", False),
            include_feedback=data.get("include_feedback", True),
            append_items_to_view=data.get("append_items_to_view", True),
            introduction_message=data.get("introduction_message"),
            completion_message=data.get("completion_message"),
            items=items,
            passing_score_percent=data.get("passing_score_percent"),
            created_by=data.get("created_by", "seeder"),
        )


# =============================================================================
# Singleton for Startup Access
# =============================================================================

_database_seeder: DatabaseSeeder | None = None
_service_provider: ServiceProviderBase | None = None


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


def set_database_seeder(seeder: DatabaseSeeder) -> None:
    """Set the singleton database seeder.

    Called during application configuration.

    Args:
        seeder: The DatabaseSeeder instance to set as singleton
    """
    global _database_seeder
    _database_seeder = seeder


class DatabaseSeederService(HostedService):
    """Hosted service that seeds the database on startup using Event Sourcing.

    Implements HostedService for automatic lifecycle management:
    - start_async(): Called on application startup to seed aggregates
    - stop_async(): Called on application shutdown (cleanup if needed)

    This service properly uses WriteModel (EventStoreDB) for seeding:
    - Aggregates are created and saved via Repository[T, str]
    - Domain events are persisted to EventStoreDB
    - Projection handlers update MongoDB ReadModel automatically
    """

    def __init__(self, service_provider: ServiceProviderBase) -> None:
        """Initialize the database seeder service.

        Args:
            service_provider: The root service provider for accessing DI container
        """
        self._service_provider = service_provider
        self._initialized = False
        self._seed_results: dict[str, int] = {}

    @property
    def seed_results(self) -> dict[str, int]:
        """Get the results from the last seeding operation."""
        return self._seed_results

    async def start_async(self) -> None:
        """Start the service by seeding the database.

        Called automatically by the Neuroglia host during application startup.
        Seeds aggregates from YAML files via the WriteModel (Event Sourcing).
        """
        try:
            # Get the DatabaseSeeder from DI container (this triggers the factory
            # which creates and registers the seeder singleton)
            seeder = self._service_provider.get_required_service(DatabaseSeeder)
            self._seed_results = await seeder.seed_all_async()
            self._initialized = True

            logger.info(
                f"✅ DatabaseSeederService started (Event Sourcing) - "
                f"skills: {self._seed_results.get('skills', 0)}, "
                f"definitions: {self._seed_results.get('definitions', 0)}, "
                f"templates: {self._seed_results.get('templates', 0)}"
            )
        except Exception as e:
            logger.error(f"❌ DatabaseSeederService failed: {e}")
            import traceback

            logger.debug(traceback.format_exc())
            # Don't raise - the app can still function

    async def stop_async(self) -> None:
        """Stop the service.

        Called automatically by the Neuroglia host during application shutdown.
        """
        logger.info("✅ DatabaseSeederService stopped")

    @staticmethod
    def configure(builder: "WebApplicationBuilder") -> "WebApplicationBuilder":
        """Configure the database seeder as a hosted service.

        The seeder is configured with access to the service provider,
        which allows it to create scopes and access repositories at runtime.

        Args:
            builder: The WebApplicationBuilder to configure

        Returns:
            The builder instance for fluent chaining
        """
        logger.info("🔧 Configuring DatabaseSeederService (Event Sourcing pattern)...")

        # Determine data directories (relative to application root)
        import os

        base_dir = Path(os.path.dirname(os.path.dirname(__file__)))  # agent-host root
        data_dir = base_dir / "data"

        # Store configuration for deferred initialization
        DatabaseSeederService._agents_dir = data_dir / "agents"
        DatabaseSeederService._templates_dir = data_dir / "templates"
        DatabaseSeederService._skills_dir = data_dir / "skills" if (data_dir / "skills").exists() else data_dir / "blueprints"

        # Register the DatabaseSeeder singleton with a factory
        def create_seeder(sp: ServiceProviderBase) -> DatabaseSeeder:
            seeder = DatabaseSeeder(
                service_provider=sp,
                agents_dir=DatabaseSeederService._agents_dir,
                templates_dir=DatabaseSeederService._templates_dir,
                skills_dir=DatabaseSeederService._skills_dir,
            )
            set_database_seeder(seeder)
            return seeder

        builder.services.add_singleton(DatabaseSeeder, implementation_factory=create_seeder)

        # Register the HostedService with a factory that injects the service provider
        def create_service(sp: ServiceProviderBase) -> DatabaseSeederService:
            return DatabaseSeederService(service_provider=sp)

        builder.services.add_singleton(HostedService, implementation_factory=create_service)

        logger.info("✅ DatabaseSeederService configured (Event Sourcing pattern)")
        return builder

    # Class-level storage for configuration (set during configure, used during start)
    _agents_dir: Path
    _templates_dir: Path
    _skills_dir: Path
