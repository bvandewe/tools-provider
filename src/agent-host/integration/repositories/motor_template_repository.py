"""MongoDB repository implementation for ConversationTemplate."""

import logging
from pathlib import Path

import yaml
from neuroglia.data.infrastructure.mongo import MotorRepository

from domain.models.conversation_template import ConversationTemplate
from domain.repositories.template_repository import TemplateRepository

logger = logging.getLogger(__name__)


class MotorTemplateRepository(MotorRepository[ConversationTemplate, str], TemplateRepository):
    """
    MongoDB-based repository for ConversationTemplate entities.

    Extends Neuroglia's MotorRepository to inherit standard CRUD operations
    and implements TemplateRepository for custom query methods.

    ConversationTemplates are state-based entities (not event-sourced) that define
    conversation structure and flow for proactive agents.
    """

    async def get_all_async(self) -> list[ConversationTemplate]:
        """Retrieve all templates from MongoDB.

        Delegates to MotorRepository's built-in get_all_async method.
        """
        return await super().get_all_async()

    async def get_by_creator_async(self, created_by: str) -> list[ConversationTemplate]:
        """Retrieve templates created by a specific user.

        Args:
            created_by: The user ID who created the templates

        Returns:
            List of ConversationTemplates created by the user, sorted by name
        """
        cursor = self.collection.find({"created_by": created_by}).sort("name", 1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_proactive_async(self) -> list[ConversationTemplate]:
        """Retrieve all proactive templates (agent_starts_first=True).

        Returns:
            List of proactive ConversationTemplates, sorted by name
        """
        cursor = self.collection.find({"agent_starts_first": True}).sort("name", 1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def get_assessments_async(self) -> list[ConversationTemplate]:
        """Retrieve all assessment templates (passing_score_percent is set).

        Returns:
            List of assessment ConversationTemplates, sorted by name
        """
        cursor = self.collection.find({"passing_score_percent": {"$ne": None}}).sort("name", 1)
        results = []
        async for doc in cursor:
            entity = self._deserialize_entity(doc)
            if entity:
                results.append(entity)
        return results

    async def seed_from_yaml_async(self, yaml_dir: str) -> int:
        """Seed templates from YAML files in a directory.

        Creates templates that don't exist (by ID). Does not update existing.
        This implements the "seed-only" strategy from the implementation plan.

        Args:
            yaml_dir: Path to directory containing template YAML files

        Returns:
            Number of templates seeded
        """
        seeded_count = 0
        yaml_path = Path(yaml_dir)

        if not yaml_path.exists():
            logger.warning(f"Template YAML directory does not exist: {yaml_dir}")
            return 0

        if not yaml_path.is_dir():
            logger.warning(f"Template YAML path is not a directory: {yaml_dir}")
            return 0

        # Find all .yaml and .yml files
        yaml_files = list(yaml_path.glob("*.yaml")) + list(yaml_path.glob("*.yml"))

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                if not data or not isinstance(data, dict):
                    logger.warning(f"Skipping invalid YAML file: {yaml_file}")
                    continue

                template_id = data.get("id")
                if not template_id:
                    logger.warning(f"Skipping YAML file without 'id': {yaml_file}")
                    continue

                # Check if template already exists
                existing = await self.get_async(template_id)
                if existing is not None:
                    logger.debug(f"Template already exists, skipping: {template_id}")
                    continue

                # Create template from YAML data
                template = ConversationTemplate.from_dict(data)
                await self.add_async(template)
                logger.info(f"Seeded template from {yaml_file.name}: {template_id} ({template.name})")
                seeded_count += 1

            except yaml.YAMLError as e:
                logger.error(f"YAML parse error in {yaml_file}: {e}")
            except Exception as e:
                logger.error(f"Error seeding template from {yaml_file}: {e}")

        logger.info(f"Template seeding complete: {seeded_count} templates seeded from {len(yaml_files)} files")
        return seeded_count
