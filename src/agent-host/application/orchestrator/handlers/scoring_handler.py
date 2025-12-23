"""Scoring handler for LLM-based response grading.

This handler evaluates user responses using an LLM to provide
intelligent, customized feedback and grading.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from application.agents.llm_provider import LlmMessage, LlmResponse
from application.orchestrator.context import ConversationContext, ItemExecutionState

if TYPE_CHECKING:
    from application.websocket.connection import Connection
    from application.websocket.manager import ConnectionManager
    from infrastructure.llm_provider_factory import LlmProviderFactory

log = logging.getLogger(__name__)


@dataclass
class ScoringResult:
    """Result of LLM-based scoring."""

    is_correct: bool
    score: float
    max_score: float
    feedback: str
    explanation: str | None = None


class ScoringHandler:
    """Handles LLM-based scoring and feedback generation.

    This handler is responsible for:
    1. Submitting user responses to the LLM for evaluation
    2. Parsing the grading response
    3. Streaming feedback to the user (if enabled)
    4. Returning scoring results for persistence

    The LLM is given context about the question, correct answer (if available),
    and the user's response to generate intelligent, personalized feedback.
    """

    def __init__(
        self,
        connection_manager: "ConnectionManager",
        llm_provider_factory: "LlmProviderFactory",
    ):
        """Initialize the scoring handler.

        Args:
            connection_manager: WebSocket connection manager for sending messages
            llm_provider_factory: Factory for creating LLM providers
        """
        self._connection_manager = connection_manager
        self._llm_provider_factory = llm_provider_factory

    async def score_item_response(
        self,
        connection: "Connection",
        context: ConversationContext,
        item_state: ItemExecutionState,
        stream_callback: Any = None,  # Callable for streaming response
    ) -> ScoringResult | None:
        """Score a user's item response using the LLM.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            item_state: The completed item execution state with responses
            stream_callback: Optional callback for streaming feedback to user

        Returns:
            ScoringResult with score and feedback, or None on error
        """
        log.info(f"🎯 Scoring item {item_state.item_id}: responses={item_state.widget_responses}")

        try:
            # Build the scoring prompt
            prompt = self._build_scoring_prompt(item_state)

            # Get LLM provider for this conversation
            model_id = context.model or "default"
            provider = self._llm_provider_factory.get_provider_for_model(model_id)

            if not provider:
                log.warning(f"No LLM provider available for scoring (model={model_id})")
                return self._create_fallback_result(item_state)

            # Build messages for LLM using LlmMessage
            messages = [
                LlmMessage.system(self._get_system_prompt()),
                LlmMessage.user(prompt),
            ]

            # Send request to LLM using chat()
            response = await provider.chat(messages=messages)

            # Parse the response
            result = self._parse_scoring_response(response, item_state)

            # Store the result in item_state
            item_state.scoring_result = {
                "is_correct": result.is_correct,
                "score": result.score,
                "max_score": result.max_score,
                "feedback": result.feedback,
                "explanation": result.explanation,
            }

            # Stream feedback to user if enabled
            if item_state.provide_feedback and stream_callback:
                await stream_callback(connection, context, result.feedback)
                log.info(f"🎯 Streamed feedback for item {item_state.item_id}")

            return result

        except Exception as e:
            log.exception(f"Error scoring item {item_state.item_id}: {e}")
            return self._create_fallback_result(item_state)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for scoring."""
        return """You are an educational assessment assistant. Your task is to evaluate a student's response to a question.

Provide your evaluation in the following format:
1. Start with whether the answer is CORRECT or INCORRECT
2. Provide a brief, encouraging explanation
3. If incorrect, hint at the right approach without giving away the answer completely

Keep your response concise (2-3 sentences max) and supportive.
Do not start with phrases like "Based on your response" or "Your answer is".
Be direct and conversational."""

    def _build_scoring_prompt(self, item_state: ItemExecutionState) -> str:
        """Build the prompt for LLM scoring.

        Args:
            item_state: The item execution state with question and response data

        Returns:
            Formatted prompt string
        """
        parts = []

        # Add the question
        if item_state.item_stem:
            parts.append(f"Question: {item_state.item_stem}")
        elif item_state.item_title:
            parts.append(f"Question: {item_state.item_title}")

        # Add the correct answer if available (for LLM context only)
        if item_state.correct_answer:
            parts.append(f"Expected answer: {item_state.correct_answer}")

        # Add the user's response(s)
        if item_state.widget_responses:
            # Format all responses
            if len(item_state.widget_responses) == 1:
                value = list(item_state.widget_responses.values())[0]
                parts.append(f"Student's answer: {value}")
            else:
                responses_str = ", ".join(str(v) for v in item_state.widget_responses.values())
                parts.append(f"Student's answers: {responses_str}")

        parts.append("\nEvaluate this response and provide feedback.")

        return "\n".join(parts)

    def _parse_scoring_response(self, response: LlmResponse, item_state: ItemExecutionState) -> ScoringResult:
        """Parse the LLM response into a ScoringResult.

        Args:
            response: The LLM response
            item_state: The item execution state

        Returns:
            Parsed ScoringResult
        """
        # Extract content from LlmResponse
        content = response.content or ""

        # Determine correctness from response
        content_lower = content.lower()
        is_correct = "correct" in content_lower and "incorrect" not in content_lower

        # Calculate score
        max_score = 1.0  # TODO: Get from item metadata
        score = max_score if is_correct else 0.0

        return ScoringResult(
            is_correct=is_correct,
            score=score,
            max_score=max_score,
            feedback=content.strip(),
            explanation=None,
        )

    def _create_fallback_result(self, item_state: ItemExecutionState) -> ScoringResult:
        """Create a fallback result when LLM scoring fails.

        Uses simple string matching against correct_answer if available.

        Args:
            item_state: The item execution state

        Returns:
            Basic ScoringResult without LLM feedback
        """
        is_correct = False
        feedback = "Response recorded."

        if item_state.correct_answer and item_state.widget_responses:
            # Simple string comparison
            user_response = str(list(item_state.widget_responses.values())[0]).strip().lower()
            correct = item_state.correct_answer.strip().lower()
            is_correct = user_response == correct
            feedback = "Correct!" if is_correct else "Not quite right."

        return ScoringResult(
            is_correct=is_correct,
            score=1.0 if is_correct else 0.0,
            max_score=1.0,
            feedback=feedback,
        )

    async def generate_score_report(
        self,
        connection: "Connection",
        context: ConversationContext,
        stream_callback: Any = None,  # Callable for streaming response
    ) -> str | None:
        """Generate a final score report for the completed conversation.

        The LLM is asked to review the entire conversation (including all
        scoring feedback messages) and generate a comprehensive summary report.

        Args:
            connection: The WebSocket connection
            context: The conversation context
            stream_callback: Optional callback for streaming the report to user

        Returns:
            The generated report text, or None on error
        """
        log.info(f"📊 Generating final score report for conversation {context.conversation_id}")

        try:
            # Get LLM provider
            model_id = context.model or "default"
            provider = self._llm_provider_factory.get_provider_for_model(model_id)

            if not provider:
                log.warning(f"No LLM provider available for score report (model={model_id})")
                return None

            # Build the report prompt using LlmMessage
            messages = [
                LlmMessage.system(self._get_report_system_prompt()),
                LlmMessage.user(self._build_report_prompt(context)),
            ]

            # Send request to LLM using chat()
            response = await provider.chat(messages=messages)

            # Extract content from LlmResponse
            report = response.content or ""

            # Stream the report to the user
            if report and stream_callback:
                await stream_callback(connection, context, report)
                log.info(f"📊 Streamed final score report for {context.conversation_id}")

            return report

        except Exception as e:
            log.exception(f"Error generating score report: {e}")
            return None

    def _get_report_system_prompt(self) -> str:
        """Get the system prompt for score report generation."""
        return """You are an educational assessment assistant generating a final performance summary.

Create a brief, encouraging summary report that includes:
1. Overall performance assessment (excellent, good, needs improvement)
2. Key strengths observed
3. Areas for improvement (if any)
4. A brief motivational closing

Keep the report concise (4-6 sentences) and maintain a positive, supportive tone.
Format the output as a readable paragraph, not a list."""

    def _build_report_prompt(self, context: ConversationContext) -> str:
        """Build the prompt for score report generation.

        Args:
            context: The conversation context

        Returns:
            Formatted prompt string
        """
        parts = [
            "Based on the conversation history and all the scoring feedback provided,",
            "generate a final performance summary report for this learning session.",
            "",
            f"Template: {context.template_config.get('name', 'Assessment')}",
            f"Total items completed: {context.current_item_index + 1}",
        ]

        # Include current item scoring result if available
        if context.current_item_state and context.current_item_state.scoring_result:
            result = context.current_item_state.scoring_result
            parts.append(f"Last item score: {result.get('score', 0)}/{result.get('max_score', 1)}")

        parts.append("")
        parts.append("Generate the summary report now.")

        return "\n".join(parts)
