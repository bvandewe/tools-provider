"""Abstract repository for ConversationTemplate read model queries.

ConversationTemplate is a state-based entity (stored in MongoDB, not event-sourced)
that defines conversation structure and flow for proactive agents.
"""

from abc import ABC, abstractmethod

from neuroglia.data.infrastructure.abstractions import Repository

from domain.models.conversation_template import ConversationTemplate


class TemplateRepository(Repository[ConversationTemplate, str], ABC):
    """Abstract repository for ConversationTemplate.

    This repository provides query methods for ConversationTemplates stored in MongoDB.
    Unlike event-sourced aggregates, ConversationTemplates are simple state-based entities.

    Templates define:
    - Flow behavior (who speaks first, navigation rules)
    - Timing constraints (min/max duration)
    - Display options (progress indicator, scoring)
    - Content structure (ordered ConversationItems with ItemContents)
    """

    @abstractmethod
    async def get_all_async(self) -> list[ConversationTemplate]:
        """Retrieve all templates from the read model."""
        pass

    @abstractmethod
    async def get_by_creator_async(self, created_by: str) -> list[ConversationTemplate]:
        """Retrieve templates created by a specific user.

        Args:
            created_by: The user ID who created the templates

        Returns:
            List of ConversationTemplates created by the user
        """
        pass

    @abstractmethod
    async def get_proactive_async(self) -> list[ConversationTemplate]:
        """Retrieve all proactive templates (agent_starts_first=True).

        Returns:
            List of proactive ConversationTemplates
        """
        pass

    @abstractmethod
    async def get_assessments_async(self) -> list[ConversationTemplate]:
        """Retrieve all assessment templates (passing_score_percent is set).

        Returns:
            List of assessment ConversationTemplates
        """
        pass

    @abstractmethod
    async def seed_from_yaml_async(self, yaml_dir: str) -> int:
        """Seed templates from YAML files in a directory.

        Creates templates that don't exist (by ID). Does not update existing.

        Args:
            yaml_dir: Path to directory containing template YAML files

        Returns:
            Number of templates seeded
        """
        pass
