"""Blueprint store service for loading exam and skill blueprints.

This service loads and caches YAML blueprint files from the data/blueprints/ directory.
It provides access to both Skill blueprints (for item generation) and
ExamBlueprint (for exam structure and configuration).
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from domain.models.blueprint_models import ExamBlueprint, Skill

logger = logging.getLogger(__name__)


class BlueprintLoadError(Exception):
    """Raised when a blueprint cannot be loaded."""

    pass


class BlueprintStore:
    """Service for loading and caching blueprint definitions.

    This service manages:
    - Loading YAML files from the blueprints directory
    - Caching parsed blueprints for performance
    - Validating blueprint structure

    Directory structure:
        data/blueprints/
        ├── skills/
        │   ├── math/
        │   │   ├── two_digit_addition.yaml
        │   │   └── ...
        │   └── networking/
        │       ├── subnet_network_address.yaml
        │       └── ...
        └── exams/
            ├── math_fundamentals.yaml
            └── networking_basics.yaml
    """

    def __init__(self, blueprints_path: Path | str | None = None):
        """Initialize the blueprint store.

        Args:
            blueprints_path: Path to blueprints directory.
                           Defaults to data/blueprints/ relative to agent-host.
        """
        if blueprints_path is None:
            # Default to data/blueprints/ relative to the agent-host package
            self._blueprints_path = Path(__file__).parent.parent.parent / "data" / "blueprints"
        else:
            self._blueprints_path = Path(blueprints_path)

        # Caches
        self._skill_cache: dict[str, Skill] = {}
        self._exam_cache: dict[str, ExamBlueprint] = {}

        logger.info(f"BlueprintStore initialized with path: {self._blueprints_path}")

    @property
    def blueprints_path(self) -> Path:
        """Get the blueprints directory path."""
        return self._blueprints_path

    def _load_yaml_file(self, file_path: Path) -> dict[str, Any]:
        """Load and parse a YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            Parsed YAML content as dictionary

        Raises:
            BlueprintLoadError: If file cannot be loaded or parsed
        """
        try:
            if not file_path.exists():
                raise BlueprintLoadError(f"Blueprint file not found: {file_path}")

            with open(file_path, encoding="utf-8") as f:
                content = yaml.safe_load(f)

            if not isinstance(content, dict):
                raise BlueprintLoadError(f"Invalid blueprint format in {file_path}: expected dict, got {type(content)}")

            return content

        except yaml.YAMLError as e:
            raise BlueprintLoadError(f"Failed to parse YAML in {file_path}: {e}") from e
        except OSError as e:
            raise BlueprintLoadError(f"Failed to read file {file_path}: {e}") from e

    def _find_skill_file(self, skill_id: str) -> Path | None:
        """Find the YAML file for a skill ID.

        Searches recursively in data/blueprints/skills/ for a file
        containing the matching skill_id.

        Args:
            skill_id: The skill ID to find

        Returns:
            Path to the skill file, or None if not found
        """
        skills_dir = self._blueprints_path / "skills"
        if not skills_dir.exists():
            return None

        # Search all YAML files in skills directory
        for yaml_file in skills_dir.rglob("*.yaml"):
            try:
                content = self._load_yaml_file(yaml_file)
                if content.get("skill_id") == skill_id:
                    return yaml_file
            except BlueprintLoadError:
                continue

        return None

    def _find_exam_file(self, exam_id: str) -> Path | None:
        """Find the YAML file for an exam ID.

        Searches in data/blueprints/exams/ for a file
        containing the matching exam_id.

        Args:
            exam_id: The exam ID to find

        Returns:
            Path to the exam file, or None if not found
        """
        exams_dir = self._blueprints_path / "exams"
        if not exams_dir.exists():
            return None

        # Search all YAML files in exams directory
        for yaml_file in exams_dir.rglob("*.yaml"):
            try:
                content = self._load_yaml_file(yaml_file)
                if content.get("exam_id") == exam_id:
                    return yaml_file
            except BlueprintLoadError:
                continue

        return None

    async def get_skill(self, skill_id: str) -> Skill:
        """Get a skill blueprint by ID.

        Args:
            skill_id: The skill identifier

        Returns:
            The Skill blueprint

        Raises:
            BlueprintLoadError: If skill cannot be found or loaded
        """
        # Check cache first
        if skill_id in self._skill_cache:
            return self._skill_cache[skill_id]

        # Find and load the skill file
        skill_file = self._find_skill_file(skill_id)
        if skill_file is None:
            raise BlueprintLoadError(f"Skill not found: {skill_id}")

        content = self._load_yaml_file(skill_file)
        skill = Skill.from_dict(content)

        # Cache and return
        self._skill_cache[skill_id] = skill
        logger.debug(f"Loaded skill: {skill_id} from {skill_file}")
        return skill

    async def get_exam(self, exam_id: str) -> ExamBlueprint:
        """Get an exam blueprint by ID.

        Args:
            exam_id: The exam identifier

        Returns:
            The ExamBlueprint

        Raises:
            BlueprintLoadError: If exam cannot be found or loaded
        """
        # Check cache first
        if exam_id in self._exam_cache:
            return self._exam_cache[exam_id]

        # Find and load the exam file
        exam_file = self._find_exam_file(exam_id)
        if exam_file is None:
            raise BlueprintLoadError(f"Exam not found: {exam_id}")

        content = self._load_yaml_file(exam_file)
        exam = ExamBlueprint.from_dict(content)

        # Cache and return
        self._exam_cache[exam_id] = exam
        logger.debug(f"Loaded exam: {exam_id} from {exam_file}")
        return exam

    async def list_exams(self) -> list[dict[str, Any]]:
        """List all available exams.

        Returns:
            List of exam summaries with id, name, description
        """
        exams_dir = self._blueprints_path / "exams"
        if not exams_dir.exists():
            return []

        results = []
        for yaml_file in exams_dir.rglob("*.yaml"):
            try:
                content = self._load_yaml_file(yaml_file)
                if "exam_id" in content:
                    results.append(
                        {
                            "exam_id": content["exam_id"],
                            "name": content.get("name", content["exam_id"]),
                            "description": content.get("description", ""),
                            "total_items": content.get("total_items", 0),
                            "time_limit_minutes": content.get("time_limit_minutes"),
                        }
                    )
            except BlueprintLoadError as e:
                logger.warning(f"Failed to load exam from {yaml_file}: {e}")
                continue

        return results

    async def list_skills(self, domain: str | None = None) -> list[dict[str, Any]]:
        """List all available skills, optionally filtered by domain.

        Args:
            domain: Optional domain filter (e.g., "Mathematics", "Networking")

        Returns:
            List of skill summaries
        """
        skills_dir = self._blueprints_path / "skills"
        if not skills_dir.exists():
            return []

        results = []
        for yaml_file in skills_dir.rglob("*.yaml"):
            try:
                content = self._load_yaml_file(yaml_file)
                if "skill_id" in content:
                    skill_domain = content.get("domain", "")
                    if domain is None or skill_domain.lower() == domain.lower():
                        results.append(
                            {
                                "skill_id": content["skill_id"],
                                "name": content.get("name", content["skill_id"]),
                                "domain": skill_domain,
                                "topic": content.get("topic", ""),
                                "description": content.get("description", ""),
                            }
                        )
            except BlueprintLoadError as e:
                logger.warning(f"Failed to load skill from {yaml_file}: {e}")
                continue

        return results

    async def validate_exam(self, exam_id: str) -> dict[str, Any]:
        """Validate an exam blueprint and its referenced skills.

        Args:
            exam_id: The exam to validate

        Returns:
            Validation result with success flag and any errors
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            exam = await self.get_exam(exam_id)
        except BlueprintLoadError as e:
            return {"valid": False, "errors": [str(e)], "warnings": []}

        # Check all referenced skills exist
        for domain in exam.domains:
            for skill_ref in domain.skills:
                try:
                    await self.get_skill(skill_ref.skill_id)
                except BlueprintLoadError:
                    errors.append(f"Skill not found: {skill_ref.skill_id} (referenced in domain {domain.domain_id})")

        # Check item counts make sense
        computed_total = exam.compute_total_items_from_domains()
        if computed_total != exam.total_items:
            warnings.append(f"total_items ({exam.total_items}) doesn't match sum of domain item_counts ({computed_total})")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "exam_id": exam_id,
            "domains": len(exam.domains),
            "skills_referenced": len(exam.get_all_skill_ids()),
        }

    def clear_cache(self) -> None:
        """Clear all cached blueprints."""
        self._skill_cache.clear()
        self._exam_cache.clear()
        logger.debug("Blueprint cache cleared")

    def reload_skill(self, skill_id: str) -> None:
        """Remove a skill from cache to force reload on next access.

        Args:
            skill_id: The skill to invalidate
        """
        self._skill_cache.pop(skill_id, None)

    def reload_exam(self, exam_id: str) -> None:
        """Remove an exam from cache to force reload on next access.

        Args:
            exam_id: The exam to invalidate
        """
        self._exam_cache.pop(exam_id, None)


# Global instance for easy access (set by configure())
_blueprint_store: BlueprintStore | None = None


def get_blueprint_store() -> BlueprintStore | None:
    """Get the global blueprint store instance."""
    return _blueprint_store


def set_blueprint_store(store: BlueprintStore) -> None:
    """Set the global blueprint store instance."""
    global _blueprint_store
    _blueprint_store = store
