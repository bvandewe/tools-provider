"""Unit tests for evaluation services.

Tests for:
- BlueprintStore
- ItemGeneratorService
- EvaluationSessionManager
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.models.blueprint_models import ExamBlueprint, ExamDomain, ExamDomainSkillRef, ItemType, Skill
from domain.models.generated_item import GeneratedItem

# =============================================================================
# BlueprintStore Tests
# =============================================================================


class TestBlueprintStore:
    """Tests for BlueprintStore service."""

    @pytest.fixture
    def mock_blueprints_path(self, tmp_path):
        """Create a temporary blueprints directory with test files."""
        skills_dir = tmp_path / "skills" / "math"
        skills_dir.mkdir(parents=True)

        exams_dir = tmp_path / "exams"
        exams_dir.mkdir(parents=True)

        # Create a test skill file
        skill_yaml = """
skill_id: MATH-TEST-001
name: Test Skill
domain: math
topic: testing
description: A test skill
item_type: multiple_choice
difficulty_levels:
  easy:
    value: 0.3
    constraints:
      - Use numbers 1-10
  medium:
    value: 0.5
    constraints:
      - Use numbers 10-50
stem_templates:
  - "What is the result?"
"""
        (skills_dir / "test_skill.yaml").write_text(skill_yaml)

        # Create a test exam file
        exam_yaml = """
exam_id: TEST-EXAM-001
name: Test Exam
description: A test exam
time_limit_minutes: 30
passing_score_percent: 70.0
domains:
  - domain_id: math
    name: Mathematics
    item_count: 3
    skills:
      - skill_id: MATH-TEST-001
"""
        (exams_dir / "test_exam.yaml").write_text(exam_yaml)

        return tmp_path

    @pytest.mark.asyncio
    async def test_load_skill(self, mock_blueprints_path):
        """Test loading a skill blueprint."""
        from application.services.blueprint_store import BlueprintStore

        store = BlueprintStore(mock_blueprints_path)
        skill = await store.get_skill("MATH-TEST-001")

        assert skill is not None
        assert skill.skill_id == "MATH-TEST-001"
        assert skill.name == "Test Skill"
        assert skill.domain == "math"

    @pytest.mark.asyncio
    async def test_load_exam(self, mock_blueprints_path):
        """Test loading an exam blueprint."""
        from application.services.blueprint_store import BlueprintStore

        store = BlueprintStore(mock_blueprints_path)
        exam = await store.get_exam("TEST-EXAM-001")

        assert exam is not None
        assert exam.exam_id == "TEST-EXAM-001"
        assert exam.name == "Test Exam"
        assert len(exam.domains) == 1
        assert exam.domains[0].item_count == 3


# =============================================================================
# EvaluationSessionManager Tests
# =============================================================================


class TestEvaluationSessionManager:
    """Tests for EvaluationSessionManager."""

    @pytest.fixture
    def mock_blueprint_store(self):
        """Create a mock blueprint store."""
        store = MagicMock()

        # Mock skill
        mock_skill = Skill(
            skill_id="MATH-ADD-001",
            name="Addition",
            domain="math",
            topic="arithmetic",
            description="Basic addition",
            item_type=ItemType.MULTIPLE_CHOICE,
            stem_templates=["What is {a} + {b}?"],
        )
        store.get_skill = AsyncMock(return_value=mock_skill)

        # Mock exam
        mock_exam = ExamBlueprint(
            exam_id="TEST-EXAM",
            name="Test Exam",
            domains=[
                ExamDomain(
                    domain_id="math",
                    name="Math",
                    item_count=2,
                    skills=[ExamDomainSkillRef(skill_id="MATH-ADD-001")],
                )
            ],
            time_limit_minutes=30,
            passing_score_percent=70.0,
        )
        store.get_exam = AsyncMock(return_value=mock_exam)

        return store

    @pytest.fixture
    def mock_item_generator(self):
        """Create a mock item generator."""
        generator = MagicMock()

        # Mock generate_item to return a GeneratedItem
        call_count = [0]

        async def mock_generate(skill_id, difficulty, domain_id):
            call_count[0] += 1
            return GeneratedItem(
                id=f"item-{call_count[0]}",
                skill_id=skill_id,
                domain_id=domain_id,
                sequence_number=call_count[0],
                generated_at=datetime.now(UTC),
                difficulty_level=difficulty,
                difficulty_value=0.5,
                item_type=ItemType.MULTIPLE_CHOICE,
                stem="What is 5 + 3?",
                options=["6", "7", "8", "9"],
                correct_answer="8",
                correct_index=2,
                explanation="5 + 3 = 8",
            )

        generator.generate_item = mock_generate
        return generator

    @pytest.mark.asyncio
    async def test_initialize_session(self, mock_blueprint_store, mock_item_generator):
        """Test initializing an evaluation session."""
        from application.services.evaluation_session_manager import EvaluationSessionManager

        manager = EvaluationSessionManager(
            blueprint_store=mock_blueprint_store,
            item_generator=mock_item_generator,
        )

        result = await manager.initialize_session(exam_id="TEST-EXAM")

        assert result["exam_id"] == "TEST-EXAM"
        assert result["total_items"] == 2
        assert result["time_limit_minutes"] == 30

    @pytest.mark.asyncio
    async def test_get_next_item(self, mock_blueprint_store, mock_item_generator):
        """Test getting the next item."""
        from application.services.evaluation_session_manager import EvaluationSessionManager

        manager = EvaluationSessionManager(
            blueprint_store=mock_blueprint_store,
            item_generator=mock_item_generator,
        )

        await manager.initialize_session(exam_id="TEST-EXAM")
        item_data = await manager.get_next_item()

        assert item_data is not None
        assert "item_id" in item_data
        assert "stem" in item_data
        assert "options" in item_data

    @pytest.mark.asyncio
    async def test_record_response(self, mock_blueprint_store, mock_item_generator):
        """Test recording a response."""
        from application.services.evaluation_session_manager import EvaluationSessionManager

        manager = EvaluationSessionManager(
            blueprint_store=mock_blueprint_store,
            item_generator=mock_item_generator,
        )

        await manager.initialize_session(exam_id="TEST-EXAM")
        item_data = await manager.get_next_item()
        assert item_data is not None
        item_id = item_data["item_id"]

        result = manager.record_response(
            item_id=item_id,
            response_index=2,  # Correct answer
        )

        assert result["recorded"] is True
        assert result["item_id"] == item_id

    @pytest.mark.asyncio
    async def test_compute_results(self, mock_blueprint_store, mock_item_generator):
        """Test computing final results."""
        from application.services.evaluation_session_manager import EvaluationSessionManager

        manager = EvaluationSessionManager(
            blueprint_store=mock_blueprint_store,
            item_generator=mock_item_generator,
        )

        await manager.initialize_session(exam_id="TEST-EXAM")

        # Complete both items
        for _ in range(2):
            item_data = await manager.get_next_item()
            assert item_data is not None
            manager.record_response(item_id=item_data["item_id"], response_index=2)

        results = manager.compute_results()

        assert results.total_items == 2
        assert results.items_completed == 2
        assert results.items_correct == 2  # Both correct
        assert results.score_percent == 100.0
        assert results.passed is True

    def test_get_tool_definitions(self):
        """Test getting tool definitions."""
        from application.services.evaluation_session_manager import EvaluationSessionManager

        tool_defs = EvaluationSessionManager.get_tool_definitions()

        assert len(tool_defs) == 3
        tool_names = [t["name"] for t in tool_defs]
        assert "get_next_item" in tool_names
        assert "record_response" in tool_names
        assert "complete_session" in tool_names
