"""Skill Loader for YAML skill file scanning and indexing.

This module provides a service that scans YAML files containing SkillTemplates
and indexes them in memory for fast lookup during conversation execution.

Skills are loaded at application startup and indexed by skill_id.
ItemContent.source_id references these skill IDs for templated content.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from domain.models.skill_template import SkillTemplate

logger = logging.getLogger(__name__)


class SkillLoader:
    """Service for loading and indexing SkillTemplates from YAML files.

    Skills are loaded once at startup and kept in memory for fast access.
    The loader scans a directory for .yaml/.yml files and parses them.

    Usage:
        loader = SkillLoader("/path/to/skills")
        await loader.load_async()
        skill = loader.get_skill("MATH.ARITH.ADD.2DIGIT")
    """

    def __init__(self, skills_dir: str | Path) -> None:
        """Initialize the skill loader.

        Args:
            skills_dir: Path to directory containing skill YAML files
        """
        self._skills_dir = Path(skills_dir)
        self._skills: dict[str, SkillTemplate] = {}
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """Check if skills have been loaded."""
        return self._loaded

    @property
    def skill_count(self) -> int:
        """Get the number of loaded skills."""
        return len(self._skills)

    @property
    def skill_ids(self) -> list[str]:
        """Get list of all loaded skill IDs."""
        return list(self._skills.keys())

    def get_skill(self, skill_id: str) -> SkillTemplate | None:
        """Get a skill by ID.

        Args:
            skill_id: The skill ID to look up

        Returns:
            The SkillTemplate if found, None otherwise
        """
        return self._skills.get(skill_id)

    def get_skills_by_domain(self, domain: str) -> list[SkillTemplate]:
        """Get all skills in a domain.

        Args:
            domain: The domain to filter by

        Returns:
            List of SkillTemplates in the domain
        """
        return [s for s in self._skills.values() if s.domain == domain]

    def get_skills_by_subdomain(self, domain: str, subdomain: str) -> list[SkillTemplate]:
        """Get all skills in a domain/subdomain.

        Args:
            domain: The domain to filter by
            subdomain: The subdomain to filter by

        Returns:
            List of SkillTemplates in the domain/subdomain
        """
        return [s for s in self._skills.values() if s.domain == domain and s.subdomain == subdomain]

    async def load_async(self) -> int:
        """Load all skills from YAML files.

        Scans the skills directory for .yaml/.yml files and parses them.
        Each file can contain a single skill or a list of skills.

        Returns:
            Number of skills loaded
        """
        if not self._skills_dir.exists():
            logger.warning(f"Skills directory does not exist: {self._skills_dir}")
            self._loaded = True
            return 0

        if not self._skills_dir.is_dir():
            logger.warning(f"Skills path is not a directory: {self._skills_dir}")
            self._loaded = True
            return 0

        # Clear existing skills
        self._skills.clear()

        # Find all YAML files
        yaml_files = list(self._skills_dir.glob("**/*.yaml")) + list(self._skills_dir.glob("**/*.yml"))

        for yaml_file in yaml_files:
            try:
                await self._load_file_async(yaml_file)
            except Exception as e:
                logger.error(f"Error loading skill file {yaml_file}: {e}")

        self._loaded = True
        logger.info(f"Loaded {len(self._skills)} skills from {len(yaml_files)} files")
        return len(self._skills)

    async def _load_file_async(self, yaml_file: Path) -> None:
        """Load skills from a single YAML file.

        Args:
            yaml_file: Path to the YAML file
        """
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return

        # Handle single skill or list of skills
        if isinstance(data, list):
            for item in data:
                await self._add_skill_from_dict(item, yaml_file)
        elif isinstance(data, dict):
            # Check if it's a container with "skills" key
            if "skills" in data and isinstance(data["skills"], list):
                for item in data["skills"]:
                    await self._add_skill_from_dict(item, yaml_file)
            else:
                # Single skill
                await self._add_skill_from_dict(data, yaml_file)

    async def _add_skill_from_dict(self, data: dict[str, Any], source_file: Path) -> None:
        """Add a skill from dictionary data.

        Args:
            data: Skill data dictionary
            source_file: Source file for logging
        """
        skill_id = data.get("id")
        if not skill_id:
            logger.warning(f"Skill without 'id' in {source_file}, skipping")
            return

        if skill_id in self._skills:
            logger.warning(f"Duplicate skill ID '{skill_id}' in {source_file}, overwriting")

        try:
            skill = SkillTemplate.from_dict(data)
            self._skills[skill_id] = skill
            logger.debug(f"Loaded skill: {skill_id} from {source_file.name}")
        except Exception as e:
            logger.error(f"Error parsing skill '{skill_id}' from {source_file}: {e}")

    async def reload_async(self) -> int:
        """Reload all skills from YAML files.

        Clears the current cache and reloads everything.

        Returns:
            Number of skills loaded
        """
        self._loaded = False
        return await self.load_async()


# =============================================================================
# Singleton Pattern for Global Access
# =============================================================================

_skill_loader: SkillLoader | None = None


def get_skill_loader() -> SkillLoader:
    """Get the singleton skill loader.

    Returns:
        The SkillLoader singleton

    Raises:
        RuntimeError: If loader not initialized
    """
    if _skill_loader is None:
        raise RuntimeError("SkillLoader not initialized. Call set_skill_loader() first.")
    return _skill_loader


def set_skill_loader(loader: SkillLoader) -> None:
    """Set the singleton skill loader.

    Args:
        loader: The SkillLoader instance to use
    """
    global _skill_loader
    _skill_loader = loader
    logger.debug("SkillLoader singleton set")
