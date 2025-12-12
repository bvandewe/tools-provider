"""Evaluation session manager for orchestrating assessment sessions.

This service manages the lifecycle of evaluation/validation sessions:
- Building the item plan from exam blueprints
- Generating items on-demand via ItemGeneratorService
- Recording responses and computing correctness
- Computing final results

The manager provides backend tool implementations for the ProactiveAgent.
"""

import logging
import random
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from application.agents.base_agent import ToolExecutionRequest, ToolExecutionResult
from application.agents.llm_provider import LlmProvider, LlmToolDefinition
from application.services.blueprint_store import BlueprintStore
from application.services.item_generator_service import ItemGeneratorService
from domain.models.blueprint_models import DifficultyLevel, ExamBlueprint
from domain.models.generated_item import DomainResult, EvaluationResults, GeneratedItem, ItemPlanEntry

logger = logging.getLogger(__name__)


# =============================================================================
# Backend Tool Definitions for Evaluation
# =============================================================================

EVALUATION_BACKEND_TOOLS: list[LlmToolDefinition] = [
    LlmToolDefinition(
        name="get_next_item",
        description="""Get the next assessment item to present to the user.
Returns the item content including stem and options (for multiple choice).
Returns null/empty if no more items remain (session complete).
IMPORTANT: Present the item EXACTLY as provided - do not modify the wording.""",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    LlmToolDefinition(
        name="record_response",
        description="""Record the user's response to the current item.
Call this AFTER the user has submitted their answer via the widget.
Returns whether there are more items or if session is complete.""",
        parameters={
            "type": "object",
            "properties": {
                "item_id": {
                    "type": "string",
                    "description": "The item ID from get_next_item",
                },
                "response_index": {
                    "type": "integer",
                    "description": "The index of the selected option (0-based)",
                },
                "response_text": {
                    "type": "string",
                    "description": "The text of the selected option or free text response",
                },
            },
            "required": ["item_id"],
        },
    ),
    LlmToolDefinition(
        name="complete_session",
        description="""Complete the evaluation session and get final results.
Call this when get_next_item returns no more items.
Returns the final score and performance summary.""",
        parameters={
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Reason for completion",
                    "enum": ["all_items_completed", "time_expired", "user_terminated"],
                },
            },
            "required": [],
        },
    ),
]


def get_evaluation_backend_tools() -> list[LlmToolDefinition]:
    """Get the backend tool definitions for evaluation sessions."""
    return EVALUATION_BACKEND_TOOLS.copy()


class EvaluationSessionManager:
    """Manages evaluation session state and backend tool execution.

    This service:
    1. Builds an item plan from exam blueprints
    2. Generates items on-demand using ItemGeneratorService
    3. Tracks current item and user responses
    4. Computes final results

    It provides a tool_executor callback for the ProactiveAgent.
    """

    def __init__(
        self,
        blueprint_store: BlueprintStore,
        item_generator: ItemGeneratorService,
    ):
        """Initialize the evaluation session manager.

        Args:
            blueprint_store: Service for loading blueprints
            item_generator: Service for generating items
        """
        self._blueprint_store = blueprint_store
        self._item_generator = item_generator

        # Session state (per-instance, created for each session)
        self._exam_blueprint: ExamBlueprint | None = None
        self._item_plan: list[ItemPlanEntry] = []
        self._generated_items: dict[str, GeneratedItem] = {}  # item_id -> item
        self._current_item_index: int = 0
        self._current_item: GeneratedItem | None = None
        self._session_started_at: datetime | None = None
        self._include_feedback: bool = False  # True for LEARNING mode

    async def initialize_session(
        self,
        exam_id: str,
        include_feedback: bool = False,
    ) -> dict[str, Any]:
        """Initialize an evaluation session from an exam blueprint.

        Args:
            exam_id: The exam blueprint ID
            include_feedback: If True, include correct answers for learning mode

        Returns:
            Session initialization data
        """
        # Load exam blueprint
        self._exam_blueprint = await self._blueprint_store.get_exam(exam_id)
        self._include_feedback = include_feedback

        # Build item plan
        self._item_plan = await self._build_item_plan(self._exam_blueprint)
        self._current_item_index = 0
        self._current_item = None
        self._generated_items = {}
        self._session_started_at = datetime.now(UTC)

        logger.info(f"Initialized evaluation session for exam {exam_id} with {len(self._item_plan)} items")

        return {
            "exam_id": exam_id,
            "exam_name": self._exam_blueprint.name,
            "total_items": len(self._item_plan),
            "time_limit_minutes": self._exam_blueprint.time_limit_minutes,
            "passing_score_percent": self._exam_blueprint.passing_score_percent,
        }

    async def _build_item_plan(self, exam: ExamBlueprint) -> list[ItemPlanEntry]:
        """Build the item generation plan from exam blueprint.

        Args:
            exam: The exam blueprint

        Returns:
            List of item plan entries in order
        """
        plan: list[ItemPlanEntry] = []
        sequence = 1

        for domain in exam.domains:
            # Determine difficulty distribution
            remaining_difficulty = domain.difficulty_distribution.copy()
            if not remaining_difficulty:
                # Default: equal distribution
                per_level = domain.item_count // 3
                remaining_difficulty = {
                    DifficultyLevel.EASY: per_level,
                    DifficultyLevel.MEDIUM: per_level + (domain.item_count % 3),
                    DifficultyLevel.HARD: per_level,
                }

            # Select skills for each item
            skill_pool = [ref.skill_id for ref in domain.skills]
            if not skill_pool:
                logger.warning(f"Domain {domain.domain_id} has no skills, skipping")
                continue

            for _ in range(domain.item_count):
                # Select difficulty
                difficulty = self._select_difficulty(remaining_difficulty)
                if difficulty in remaining_difficulty:
                    remaining_difficulty[difficulty] = max(0, remaining_difficulty[difficulty] - 1)

                # Select skill (round-robin or random)
                skill_id = random.choice(skill_pool)  # nosec B311

                plan.append(
                    ItemPlanEntry(
                        skill_id=skill_id,
                        domain_id=domain.domain_id,
                        difficulty_level=difficulty,
                        sequence_number=sequence,
                    )
                )
                sequence += 1

        # Shuffle if configured
        if exam.shuffle_items:
            random.shuffle(plan)  # nosec B311
            # Re-sequence after shuffle
            for i, entry in enumerate(plan):
                plan[i] = ItemPlanEntry(
                    skill_id=entry.skill_id,
                    domain_id=entry.domain_id,
                    difficulty_level=entry.difficulty_level,
                    sequence_number=i + 1,
                )

        return plan

    def _select_difficulty(self, remaining: dict[DifficultyLevel, int]) -> DifficultyLevel:
        """Select a difficulty level based on remaining counts.

        Args:
            remaining: Remaining counts per difficulty

        Returns:
            Selected difficulty level
        """
        available = {level: count for level, count in remaining.items() if count > 0}
        if not available:
            return DifficultyLevel.MEDIUM

        levels = list(available.keys())
        weights = list(available.values())
        return random.choices(levels, weights=weights, k=1)[0]  # nosec B311

    async def get_next_item(self) -> dict[str, Any] | None:
        """Get the next item to present.

        Returns:
            Item presentation data, or None if no more items
        """
        if self._current_item_index >= len(self._item_plan):
            return None

        # Get plan entry
        plan_entry = self._item_plan[self._current_item_index]

        # Generate item
        try:
            item = await self._item_generator.generate_item(
                skill_id=plan_entry.skill_id,
                domain_id=plan_entry.domain_id,
                sequence_number=plan_entry.sequence_number,
                difficulty_level=plan_entry.difficulty_level,
            )
        except Exception as e:
            logger.error(f"Failed to generate item: {e}")
            # Skip this item and try next
            self._current_item_index += 1
            return await self.get_next_item()

        # Store and track
        self._generated_items[item.id] = item
        self._current_item = item

        # Prepare presentation data
        result = item.to_presentation_dict(include_answer=self._include_feedback)
        result["total_items"] = len(self._item_plan)
        result["items_remaining"] = len(self._item_plan) - self._current_item_index - 1

        logger.debug(f"Presenting item {item.id}, sequence {plan_entry.sequence_number}/{len(self._item_plan)}")
        return result

    def record_response(
        self,
        item_id: str,
        response_index: int | None = None,
        response_text: str | None = None,
        response_time_ms: float | None = None,
    ) -> dict[str, Any]:
        """Record a user's response to an item.

        Args:
            item_id: The item being responded to
            response_index: Index of selected option (multiple choice)
            response_text: Text of response
            response_time_ms: Time taken to respond

        Returns:
            Response result with correctness (for learning mode)
        """
        item = self._generated_items.get(item_id)
        if item is None:
            return {"error": f"Item not found: {item_id}"}

        # Determine response text from index if not provided
        if response_text is None and response_index is not None and item.options:
            if 0 <= response_index < len(item.options):
                response_text = item.options[response_index]

        # Record response
        item.record_response(
            user_response=response_text or "",
            user_response_index=response_index,
            response_time_ms=response_time_ms,
        )

        # Advance to next item
        self._current_item_index += 1
        has_more = self._current_item_index < len(self._item_plan)

        result: dict[str, Any] = {
            "recorded": True,
            "item_id": item_id,
            "has_more_items": has_more,
            "items_completed": self._current_item_index,
            "total_items": len(self._item_plan),
        }

        # Include feedback for learning mode
        if self._include_feedback:
            result["is_correct"] = item.is_correct
            result["correct_answer"] = item.correct_answer
            result["explanation"] = item.explanation

        return result

    def compute_results(self) -> EvaluationResults:
        """Compute final session results.

        Returns:
            Evaluation results summary
        """
        total_items = len(self._item_plan)
        items_completed = sum(1 for item in self._generated_items.values() if item.responded_at is not None)
        items_correct = sum(1 for item in self._generated_items.values() if item.is_correct is True)

        # Compute score
        score_percent = (items_correct / total_items * 100) if total_items > 0 else 0.0
        passing_score = self._exam_blueprint.passing_score_percent if self._exam_blueprint else 70.0
        passed = score_percent >= passing_score

        # Compute time
        time_elapsed = 0.0
        if self._session_started_at:
            time_elapsed = (datetime.now(UTC) - self._session_started_at).total_seconds()

        # Compute per-domain results
        domain_results: dict[str, DomainResult] = {}
        if self._exam_blueprint:
            for domain in self._exam_blueprint.domains:
                domain_results[domain.domain_id] = DomainResult(
                    domain_id=domain.domain_id,
                    domain_name=domain.name,
                )

        for item in self._generated_items.values():
            if item.domain_id in domain_results:
                dr = domain_results[item.domain_id]
                if item.responded_at is not None:
                    domain_results[item.domain_id] = DomainResult(
                        domain_id=dr.domain_id,
                        domain_name=dr.domain_name,
                        items_attempted=dr.items_attempted + 1,
                        items_correct=dr.items_correct + (1 if item.is_correct else 0),
                        total_time_ms=dr.total_time_ms + (item.response_time_ms or 0),
                    )

        return EvaluationResults(
            total_items=total_items,
            items_completed=items_completed,
            items_correct=items_correct,
            score_percent=score_percent,
            passed=passed,
            time_elapsed_seconds=time_elapsed,
            domain_results=list(domain_results.values()),
        )

    def get_state_snapshot(self) -> dict[str, Any]:
        """Get a snapshot of current session state for persistence.

        Returns:
            State dictionary
        """
        return {
            "exam_id": self._exam_blueprint.exam_id if self._exam_blueprint else None,
            "item_plan": [e.to_dict() for e in self._item_plan],
            "generated_items": {item_id: item.to_dict() for item_id, item in self._generated_items.items()},
            "current_item_index": self._current_item_index,
            "current_item_id": self._current_item.id if self._current_item else None,
            "session_started_at": self._session_started_at.isoformat() if self._session_started_at else None,
            "include_feedback": self._include_feedback,
        }

    async def restore_from_state(self, state: dict[str, Any]) -> None:
        """Restore session state from a snapshot.

        Args:
            state: State dictionary from get_state_snapshot
        """
        exam_id = state.get("exam_id")
        if exam_id:
            self._exam_blueprint = await self._blueprint_store.get_exam(exam_id)

        self._item_plan = [ItemPlanEntry.from_dict(e) for e in state.get("item_plan", [])]
        self._generated_items = {item_id: GeneratedItem.from_dict(item_data) for item_id, item_data in state.get("generated_items", {}).items()}
        self._current_item_index = state.get("current_item_index", 0)
        self._include_feedback = state.get("include_feedback", False)

        current_item_id = state.get("current_item_id")
        if current_item_id and current_item_id in self._generated_items:
            self._current_item = self._generated_items[current_item_id]

        started_at = state.get("session_started_at")
        if started_at:
            self._session_started_at = datetime.fromisoformat(started_at)

    def create_tool_executor(self) -> Any:
        """Create a tool executor callback for the ProactiveAgent.

        Returns:
            Async generator function for tool execution
        """

        async def execute_tool(request: ToolExecutionRequest) -> AsyncIterator[ToolExecutionResult]:
            """Execute evaluation backend tools."""
            import json
            import time

            start_time = time.time()

            try:
                if request.tool_name == "get_next_item":
                    item_data = await self.get_next_item()
                    if item_data is None:
                        result_content = json.dumps({"no_more_items": True, "message": "All items completed"})
                    else:
                        result_content = json.dumps(item_data)

                elif request.tool_name == "record_response":
                    args = request.arguments
                    result = self.record_response(
                        item_id=args.get("item_id", ""),
                        response_index=args.get("response_index"),
                        response_text=args.get("response_text"),
                    )
                    result_content = json.dumps(result)

                elif request.tool_name == "complete_session":
                    results = self.compute_results()
                    result_content = json.dumps(results.to_dict())

                else:
                    result_content = json.dumps({"error": f"Unknown tool: {request.tool_name}"})

                execution_time_ms = (time.time() - start_time) * 1000

                yield ToolExecutionResult(
                    call_id=request.call_id,
                    tool_name=request.tool_name,
                    success=True,
                    result=result_content,
                    execution_time_ms=execution_time_ms,
                )

            except Exception as e:
                logger.error(f"Tool execution failed for {request.tool_name}: {e}")
                yield ToolExecutionResult(
                    call_id=request.call_id,
                    tool_name=request.tool_name,
                    success=False,
                    error=str(e),
                )

        return execute_tool

    @staticmethod
    def get_tool_definitions() -> list[dict[str, Any]]:
        """Get the LLM tool definitions for evaluation backend tools.

        These definitions describe the tools available to the agent for
        managing the evaluation session.

        Returns:
            List of tool definition dictionaries for LLM
        """
        return [
            {
                "name": "get_next_item",
                "description": "Fetch the next assessment item from the session plan. Returns the item data including stem, options, and metadata. Returns null if all items have been completed.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "record_response",
                "description": "Record the user's response to an assessment item after they submit their answer via the multiple_choice widget.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The unique identifier of the item being responded to",
                        },
                        "response_index": {
                            "type": "integer",
                            "description": "The 0-based index of the selected option",
                        },
                        "response_text": {
                            "type": "string",
                            "description": "The text of the selected response option",
                        },
                    },
                    "required": ["item_id"],
                },
            },
            {
                "name": "complete_session",
                "description": "Compute and return the final evaluation results. Call this when all items are completed or the user requests to end the session.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        ]


# Factory function for creating per-session managers
def create_evaluation_manager(
    blueprint_store: BlueprintStore,
    llm_provider: LlmProvider,
) -> EvaluationSessionManager:
    """Create an evaluation session manager.

    Args:
        blueprint_store: Shared blueprint store
        llm_provider: LLM provider for item generation

    Returns:
        New EvaluationSessionManager instance
    """
    item_generator = ItemGeneratorService(blueprint_store, llm_provider)
    return EvaluationSessionManager(blueprint_store, item_generator)
